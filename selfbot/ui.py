"""
Minimal logging for commercial solo workers.
"""

from datetime import datetime

def log_worker_event(worker_id, msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    tag = f"[W#{worker_id}]" if isinstance(worker_id, int) else f"[{worker_id}]"
    print(f"{ts} {tag} [{level}] {msg}")


def log_info(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} [SYS] [INFO] {msg}")


def log_warn(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} [SYS] [WARN] {msg}")


def log_error(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} [SYS] [ERROR] {msg}")


def log_success(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} [SYS] [SUCCESS] {msg}")
