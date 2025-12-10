"""Download orchestration logic using aria2c RPC."""

from __future__ import annotations

import subprocess
import time
import xmlrpc.client
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional
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


def _coerce_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _collect_entries(value: Any) -> list[Mapping[str, Any]]:
    entries: list[Mapping[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                entries.append(item)
    return entries


def _extract_file_entries(entry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    files_value = entry.get("files")
    if not isinstance(files_value, list):
        return []
    return [file_entry for file_entry in files_value if isinstance(file_entry, Mapping)]


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
            DownloadColumn(binary_units=True),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=self._console,
            transient=not verbose,
        )
        self._tasks: dict[str, TaskID] = {}
        self._completed: dict[str, dict[str, str]] = {}
        self._failed: dict[str, dict[str, str]] = {}
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
        self._client = xmlrpc.client.ServerProxy(f"http://{LOCALHOST}:{port}/rpc", allow_none=True)
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
    def _rpc(self, method: str, *params: object) -> Any:
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
    def add_urls(self, urls: Iterable[str]) -> list[str]:
        """Submit URLs to aria2c download queue."""

        if not self._running:
            raise RuntimeError("AriaDownloader must be started before adding URLs")

        added: list[str] = []
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

        active = _collect_entries(self._rpc("aria2.tellActive"))
        waiting = _collect_entries(self._rpc("aria2.tellWaiting", 0, 1000))
        stopped = _collect_entries(self._rpc("aria2.tellStopped", 0, 1000))

        for entry in waiting:
            self._ensure_task(entry, status="waiting")

        for entry in active:
            self._ensure_task(entry, status="active")
            self._update_task_progress(entry)

        self._process_stopped(stopped)
        self._progress.refresh()
        return bool(active or waiting)

    def wait_for_completion(self) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
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

    def get_results(self) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Return completed and failed download metadata."""

        return list(self._completed.values()), list(self._failed.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_task(self, entry: Mapping[str, Any], status: str) -> None:
        gid_obj = entry.get("gid")
        if not isinstance(gid_obj, str):
            return

        gid = gid_obj
        task_id = self._tasks.get(gid)
        total_length = _coerce_int(entry.get("totalLength"))
        description = self._build_description(entry, status=status)
        completed = _coerce_float(entry.get("completedLength"))

        if task_id is None:
            total = float(total_length) if total_length > 0 else 0.0
            task_id = self._progress.add_task(description, total=total)
            self._tasks[gid] = task_id
        self._progress.update(task_id, description=description, completed=completed)

    def _build_description(self, entry: Mapping[str, Any], status: str) -> str:
        filename = ""
        for file_entry in _extract_file_entries(entry):
            path_value = file_entry.get("path")
            if isinstance(path_value, str) and path_value:
                filename = Path(path_value).name
                break
        if not filename:
            filename = _coerce_str(entry.get("gid"), default="unknown")
        status_label = status.upper()
        return f"{filename} [{status_label}]"

    def _update_task_progress(self, entry: Mapping[str, Any]) -> None:
        gid_obj = entry.get("gid")
        if not isinstance(gid_obj, str) or gid_obj not in self._tasks:
            return

        gid = gid_obj
        task_id = self._tasks[gid]
        completed = _coerce_float(entry.get("completedLength"))
        total = _coerce_float(entry.get("totalLength"))
        if total > 0:
            self._progress.update(task_id, completed=completed, total=total)
        else:
            self._progress.update(task_id, completed=completed)

    def _process_stopped(self, entries: Iterable[Mapping[str, Any]]) -> None:
        for entry in entries:
            gid_obj = entry.get("gid")
            if not isinstance(gid_obj, str) or gid_obj in self._processed_stopped:
                continue

            gid = gid_obj
            self._processed_stopped.add(gid)
            status = _coerce_str(entry.get("status"), default="unknown")
            path = ""
            for file_entry in _extract_file_entries(entry):
                path_value = file_entry.get("path")
                if isinstance(path_value, str):
                    path = path_value
                    break

            record: dict[str, str] = {
                "gid": gid,
                "path": path,
                "status": status,
                "totalLength": _coerce_str(entry.get("totalLength"), default="0"),
                "completedLength": _coerce_str(entry.get("completedLength"), default="0"),
                "errorCode": _coerce_str(entry.get("errorCode")),
                "errorMessage": _coerce_str(entry.get("errorMessage")),
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
