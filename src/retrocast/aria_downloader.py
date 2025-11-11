"""Download orchestration logic using aria2c RPC."""

from __future__ import annotations

import subprocess
import time
import xmlrpc.client
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from retrocast.ariafetcher import LOCALHOST, start_aria2c_ephemeral_rpc, stop_aria2c
from retrocast.logging_config import get_logger


class AriaDownloader:
    """Manage aria2c subprocess and coordinate downloads via XML-RPC."""

    def __init__(
        self,
        directory: Path,
        max_concurrent: int = 5,
        secret: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be greater than zero")

        self.directory = directory
        self.max_concurrent = max_concurrent
        self.secret = secret
        self.verbose = verbose
        self._proc: Optional[subprocess.Popen] = None
        self._port: Optional[int] = None
        self._client: Optional[xmlrpc.client.ServerProxy] = None
        self._token = f"token:{secret}" if secret else None
        self._logger = get_logger(self.__class__.__name__)
        self._console = Console(stderr=True)
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(binary=True),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=self._console,
            transient=not verbose,
        )
        self._tasks: Dict[str, TaskID] = {}
        self._completed: Dict[str, Dict[str, str]] = {}
        self._failed: Dict[str, Dict[str, str]] = {}
        self._processed_stopped: set[str] = set()
        self._running = False

    # ------------------------------------------------------------------
    # Process lifecycle helpers
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Launch aria2c subprocess and establish RPC client."""

        if self._running:
            raise RuntimeError("AriaDownloader has already been started")

        extra_args = [
            f"--max-concurrent-downloads={self.max_concurrent}",
        ]

        self.directory.mkdir(parents=True, exist_ok=True)
        proc, port = start_aria2c_ephemeral_rpc(secret=self.secret, extra_args=extra_args)
        self._proc = proc
        self._port = port
        self._client = xmlrpc.client.ServerProxy(
            f"http://{LOCALHOST}:{port}/rpc", allow_none=True
        )
        self._running = True
        self._logger.debug("aria2c RPC client connected on port {}", port)

    def stop(self) -> None:
        """Terminate aria2c subprocess if it is running."""

        if not self._running:
            return

        if self._proc is not None:
            stop_aria2c(self._proc)
        self._proc = None
        self._client = None
        self._running = False
        self._logger.debug("aria2c subprocess stopped")

    # ------------------------------------------------------------------
    # RPC helpers
    # ------------------------------------------------------------------
    def _rpc(self, method: str, *params):  # type: ignore[no-untyped-def]
        if self._client is None:
            raise RuntimeError("aria2c RPC client is not initialized")

        if self._token:
            params = (self._token, *params)
        try:
            return getattr(self._client, method)(*params)
        except (xmlrpc.client.Error, OSError) as exc:
            self._logger.error("aria2 RPC call {} failed: {}", method, exc)
            raise RuntimeError("aria2 RPC communication failed") from exc

    # ------------------------------------------------------------------
    # Download management
    # ------------------------------------------------------------------
    def add_urls(self, urls: Iterable[str]) -> List[str]:
        """Submit URLs to aria2c download queue."""

        if not self._running:
            raise RuntimeError("AriaDownloader must be started before adding URLs")

        added: List[str] = []
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                self._logger.warning("Skipping invalid URL: {}", url)
                continue

            options = {
                "dir": str(self.directory),
                "continue": "true",
                "check-integrity": "true",
            }
            gid = self._rpc("aria2.addUri", [url], options)
            added.append(gid)
            self._logger.debug("Queued {} as GID {}", url, gid)

        return added

    def monitor_progress(self) -> bool:
        """Poll download status, update progress bars, and return running state."""

        if not self._running:
            raise RuntimeError("AriaDownloader is not running")

        active = self._rpc("aria2.tellActive")
        waiting = self._rpc("aria2.tellWaiting", 0, 1000)
        stopped = self._rpc("aria2.tellStopped", 0, 1000)

        for entry in waiting:
            self._ensure_task(entry, status="waiting")

        for entry in active:
            self._ensure_task(entry, status="active")
            self._update_task_progress(entry)

        self._process_stopped(stopped)
        self._progress.refresh()
        return bool(active or waiting)

    def wait_for_completion(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Block until downloads finish and return completion summary."""

        if not self._running:
            raise RuntimeError("AriaDownloader has not been started")

        self._progress.start()
        try:
            while True:
                still_running = self.monitor_progress()
                if not still_running:
                    break
                time.sleep(0.5)

            # One final poll to capture freshly stopped transfers
            self.monitor_progress()
        finally:
            self._progress.stop()

        return self.get_results()

    def get_results(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Return completed and failed download metadata."""

        return list(self._completed.values()), list(self._failed.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_task(self, entry: Dict[str, str], status: str) -> None:
        gid = entry.get("gid")
        if not gid:
            return

        task_id = self._tasks.get(gid)
        total_length = int(entry.get("totalLength", "0"))
        description = self._build_description(entry, status=status)
        completed = float(entry.get("completedLength", "0"))

        if task_id is None:
            total = float(total_length) if total_length > 0 else 0
            task_id = self._progress.add_task(description, total=total)
            self._tasks[gid] = task_id
        self._progress.update(task_id, description=description, completed=completed)

    def _build_description(self, entry: Dict[str, str], status: str) -> str:
        files = entry.get("files", []) or []
        filename = ""
        if files:
            path = files[0].get("path")  # type: ignore[index]
            if path:
                filename = Path(path).name
        if not filename:
            filename = entry.get("gid", "unknown")
        status_label = status.upper()
        return f"{filename} [{status_label}]"

    def _update_task_progress(self, entry: Dict[str, str]) -> None:
        gid = entry.get("gid")
        if not gid or gid not in self._tasks:
            return

        task_id = self._tasks[gid]
        completed = float(entry.get("completedLength", "0"))
        total = float(entry.get("totalLength", "0"))
        if total > 0:
            self._progress.update(task_id, completed=completed, total=total)
        else:
            self._progress.update(task_id, completed=completed)

    def _process_stopped(self, entries: Iterable[Dict[str, str]]) -> None:
        for entry in entries:
            gid = entry.get("gid")
            if not gid or gid in self._processed_stopped:
                continue

            self._processed_stopped.add(gid)
            status = entry.get("status", "unknown")
            files = entry.get("files", []) or []
            path = ""
            if files:
                path = files[0].get("path", "")  # type: ignore[index]

            record = {
                "gid": gid,
                "path": path,
                "status": status,
                "totalLength": entry.get("totalLength", "0"),
                "completedLength": entry.get("completedLength", "0"),
                "errorCode": entry.get("errorCode", ""),
                "errorMessage": entry.get("errorMessage", ""),
            }

            task_id = self._tasks.get(gid)
            if task_id is not None:
                description = self._build_description(entry, status=status)
                self._progress.update(task_id, description=description)
                self._progress.stop_task(task_id)

            if status == "complete":
                self._completed[gid] = record
                self._logger.info("Completed download {}", path or gid)
            else:
                self._failed[gid] = record
                self._logger.error(
                    "Download failed for {} (code {}): {}",
                    path or gid,
                    record.get("errorCode"),
                    record.get("errorMessage"),
                )


__all__ = ["AriaDownloader"]

