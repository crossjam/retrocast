# launch_aria2c_ephemeral_rpc_xmlrpc_stamina.py
from __future__ import annotations

import os
import random
import socket
import subprocess
import sys
import time
import xmlrpc.client
from typing import List, Optional, Tuple

import stamina  # pip install stamina

from retrocast.logging_config import get_logger

LOCALHOST = "127.0.0.1"
LOGGER = get_logger(__name__)


# --- helpers ----------------------------------------------------------


def system_ephemeral_range() -> range:
    if os.name == "posix":
        try:
            with open("/proc/sys/net/ipv4/ip_local_port_range", "r") as f:
                lo, hi = map(int, f.read().split())
                return range(lo, hi + 1)
        except Exception:
            pass
    return range(30_000, 60_999)


def random_port() -> int:
    rng = system_ephemeral_range()
    return random.randint(rng.start, rng.stop - 1)


@stamina.retry(
    on=(OSError, ConnectionRefusedError, TimeoutError), wait_initial=0.05, wait_max=1.0, timeout=3.0
)
def tcp_ready(host: str, port: int) -> bool:
    """Return True when a TCP connection succeeds; raises to trigger stamina retries."""
    with socket.create_connection((host, port), timeout=0.25):
        return True


@stamina.retry(
    on=(ConnectionError, xmlrpc.client.ProtocolError, xmlrpc.client.Fault, OSError),
    wait_initial=0.1,
    wait_max=1.5,
    timeout=3.0,
)
def xmlrpc_ready(host: str, port: int, secret: Optional[str] = None) -> bool:
    """
    Ping aria2c via XML-RPC (aria2.getVersion). If --rpc-secret is used, pass 'token:SECRET'.
    Raises on failure so stamina retries automatically.
    """
    url = f"http://{host}:{port}/rpc"
    proxy = xmlrpc.client.ServerProxy(url, allow_none=True)
    params = [f"token:{secret}"] if secret else []
    result = proxy.aria2.getVersion(*params)
    if not isinstance(result, dict) or "version" not in result:
        raise ConnectionError("aria2c RPC not returning expected structure")
    return True


def build_aria2c_cmd(
    port: int, secret: Optional[str] = None, extra: Optional[List[str]] = None
) -> List[str]:
    cmd = [
        "aria2c",
        "--enable-rpc=true",
        f"--rpc-listen-port={port}",
        "--rpc-listen-all=false",  # bind to loopback only
        "--disable-ipv6=false",
        "--check-integrity=true",
        "--continue=true",
    ]
    if secret:
        cmd.append(f"--rpc-secret={secret}")
    if extra:
        cmd.extend(extra)
    return cmd


def _kill(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=1.5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# --- main startup logic with stamina -----------------------------------


@stamina.retry(
    on=(RuntimeError,),
    attempts=5,
    wait_initial=0.1,
    wait_max=2.0,
)
def start_aria2c_ephemeral_rpc(
    secret: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Tuple[subprocess.Popen, int]:
    """
    Start aria2c on a random high port and verify via XML-RPC.
    Retries automatically (exponential backoff) on bind/readiness failures.
    """
    port = random_port()
    LOGGER.debug("Starting aria2c on port {}", port)
    try:
        proc = subprocess.Popen(
            build_aria2c_cmd(port, secret=secret, extra=extra_args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        LOGGER.error("aria2c binary not found: {}", exc)
        raise RuntimeError("aria2c executable is required but was not found in PATH") from exc

    # Fast-fail if it dies immediately (e.g., EADDRINUSE)
    time.sleep(0.1)
    if proc.poll() is not None:
        err = (proc.stderr.read() if proc.stderr else "").strip()
        LOGGER.error(
            "aria2c exited early (rc={}, port={}): {}", proc.returncode, port, err or "<no stderr>"
        )
        raise RuntimeError(f"aria2c exited early (rc={proc.returncode}) on port {port}: {err}")

    # 1) Wait for TCP to accept (handled by stamina-decorated tcp_ready)
    try:
        tcp_ready(LOCALHOST, port)
    except Exception as _e:
        _kill(proc)
        LOGGER.error("aria2c not accepting TCP on port {}", port)
        raise RuntimeError(f"aria2c not accepting TCP on {port}") from _e

    # 2) Verify the XML-RPC endpoint is actually live (also stamina-decorated)
    try:
        xmlrpc_ready(LOCALHOST, port, secret=secret)
    except Exception as _e:
        _kill(proc)
        LOGGER.error("aria2c XML-RPC not responding on port {}", port)
        raise RuntimeError(f"aria2c XML-RPC not responding on {port}") from _e

    LOGGER.info("aria2c XML-RPC ready at http://{}:{}/rpc (pid={})", LOCALHOST, port, proc.pid)
    return proc, port


# --- example ----------------------------------------------------------


def main():
    SECRET = None  # set to your --rpc-secret if used
    try:
        proc, port = start_aria2c_ephemeral_rpc(secret=SECRET)
        LOGGER.info(
            "aria2c XML-RPC ready at http://{}:{}/rpc (pid={})", LOCALHOST, port, proc.pid
        )
    except RuntimeError as e:
        LOGGER.error("Failed to start aria2c: {}", e)
        sys.exit(1)
    finally:
        try:
            stop_aria2c(proc)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            LOGGER.debug("Failed to stop aria2c cleanly: {}", exc)


def stop_aria2c(proc: subprocess.Popen) -> None:
    """Terminate the aria2c subprocess."""

    _kill(proc)


if __name__ == "__main__":
    main()
