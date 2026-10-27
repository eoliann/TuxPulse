#!/usr/bin/env python3
import datetime
import json
import os
import pwd
import shutil
import socket
import subprocess

SOCKET_PATH = "/run/tuxpulse.sock"
LOG_FILE = "/var/log/tuxpulse-helper.log"
ALLOWED_BASE = {"apt", "pacman", "dnf", "zypper", "flatpak", "journalctl", "systemctl"}
ALLOWED_PREFIXES = (
    ["apt", "install"],
    ["apt", "remove"],
    ["apt", "purge"],
    ["apt", "autoremove"],
    ["pacman", "-S"],
    ["pacman", "-R"],
    ["pacman", "-Rns"],
    ["dnf", "install"],
    ["dnf", "remove"],
    ["dnf", "upgrade"],
    ["dnf", "autoremove"],
    ["zypper", "--non-interactive", "install"],
    ["zypper", "--non-interactive", "remove"],
    ["zypper", "--non-interactive", "update"],
    ["flatpak", "install"],
    ["flatpak", "uninstall"],
    ["flatpak", "update"],
    ["journalctl", "--vacuum-time=7d"],
    ["systemctl"],
)


def _log(user: str, action: str, cmd: list[str], output: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.datetime.now().isoformat()} | {user} | {action} | {' '.join(cmd)}\n")
            if output:
                handle.write(output.rstrip() + "\n")
            handle.write("\n")
    except Exception:
        pass


def _peer_user(conn) -> str:
    try:
        creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        uid = int.from_bytes(creds[4:8], "little")
        return pwd.getpwuid(uid).pw_name
    except Exception:
        return "unknown"


def _validate(cmd: list[str]) -> bool:
    if not cmd or cmd[0] not in ALLOWED_BASE:
        return False
    if cmd[0] == "flatpak" and shutil.which("flatpak") is None:
        return False
    for prefix in ALLOWED_PREFIXES:
        if cmd[: len(prefix)] == prefix:
            return True
    return False


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def _handle(conn, payload: dict) -> dict:
    action = payload.get("action")
    cmd = payload.get("cmd") or []
    user = _peer_user(conn)

    if action not in {"run", "install", "maintenance", "remove", "update", "cleanup"}:
        return {"code": 1, "output": "Invalid action"}
    if not isinstance(cmd, list) or not _validate(cmd):
        return {"code": 1, "output": "Blocked command"}

    code, output = _run(cmd)
    _log(user, action, cmd, output)
    return {"code": code, "output": output}


def main() -> None:
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o666)
    server.listen(10)
    while True:
        conn, _ = server.accept()
        try:
            data = conn.recv(1024 * 1024)
            payload = json.loads(data.decode("utf-8")) if data else {}
            response = _handle(conn, payload)
        except Exception as exc:
            response = {"code": 1, "output": str(exc)}
        conn.sendall(json.dumps(response).encode("utf-8"))
        conn.close()


if __name__ == "__main__":
    main()
