from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.privilege import elevated_command


def get_cleaner_targets():
    return [
        {
            "name": "Thumbnail cache",
            "path": str(Path.home() / ".cache" / "thumbnails"),
            "requires_root": False,
        },
        {
            "name": "User cache",
            "path": str(Path.home() / ".cache"),
            "requires_root": False,
        },
        {
            "name": "Trash",
            "path": str(Path.home() / ".local/share/Trash"),
            "requires_root": False,
        },
        {
            "name": "Temporary files",
            "path": "/tmp",
            "requires_root": True,
        },
        {
            "name": "Vacuum journal (7 days)",
            "path": "journalctl --vacuum-time=7d",
            "requires_root": True,
        },
        {
            "name": "Remove orphan packages",
            "path": "package-orphans",
            "requires_root": True,
        },
    ]


def _clear_directory(path: Path):
    if not path.exists() or not path.is_dir():
        return

    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            try:
                item.unlink()
            except OSError:
                pass


def empty_trash():
    trash_root = Path.home() / ".local/share/Trash"
    _clear_directory(trash_root / "files")
    _clear_directory(trash_root / "info")


def clean_target(target_name):
    if target_name == "Trash":
        return {"kind": "python", "name": target_name}
    if target_name == "Vacuum journal (7 days)":
        return vacuum_journal(days=7)
    if target_name == "Remove orphan packages":
        return cleanup_orphan_packages()

    for target in get_cleaner_targets():
        if target["name"] != target_name:
            continue

        path = Path(target["path"])

        if target["requires_root"]:
            return {
                "kind": "command",
                "command": [
                    "find",
                    str(path),
                    "-mindepth",
                    "1",
                    "-maxdepth",
                    "1",
                    "-exec",
                    "rm",
                    "-rf",
                    "{}",
                    "+",
                ],
                "requires_root": True,
            }

        if path.name == "cache" and str(path) == str(Path.home() / ".cache"):
            if path.exists() and path.is_dir():
                for item in path.iterdir():
                    if item.name == "Trash":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        try:
                            item.unlink()
                        except OSError:
                            pass
            return None

        _clear_directory(path)
        return None

    return None


def vacuum_journal(days=7):
    return {
        "kind": "command",
        "command": ["journalctl", f"--vacuum-time={days}d"],
        "requires_root": True,
    }


def run_clean_command(command, output_callback=None):
    if isinstance(command, dict) and command.get("kind") == "python":
        if output_callback:
            output_callback(f">>> {command.get('name', 'task')}")
        if command.get("name") == "Trash":
            empty_trash()
        return 0

    if command is None:
        return 0

    if isinstance(command, dict) and command.get("kind") == "orphans":
        orphans = _list_orphan_packages(command.get("pm"))
        if not orphans:
            if output_callback:
                output_callback("No orphan packages found.")
            return 0
        command = {
            "kind": "command",
            "command": _orphan_remove_command(command.get("pm"), orphans),
            "requires_root": True,
        }

    requires_root = False
    actual_command = command

    if isinstance(command, dict) and command.get("kind") == "command":
        actual_command = list(command.get("command", []))
        requires_root = bool(command.get("requires_root"))
    elif isinstance(command, (list, tuple)):
        actual_command = list(command)

    try:
        if requires_root:
            actual_command = elevated_command(actual_command)
    except RuntimeError as exc:
        if output_callback:
            output_callback(str(exc))
        raise

    process = subprocess.Popen(
        actual_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if process.stdout is not None:
        for line in process.stdout:
            if output_callback:
                output_callback(line.rstrip("\n"))

    process.wait()
    return process.returncode


def cleanup_orphan_packages():
    from core.pkg_backend import PackageBackend

    pm = PackageBackend().pm

    if pm == "apt":
        return {
            "kind": "command",
            "command": ["apt", "autoremove", "-y"],
            "requires_root": True,
        }

    if pm in ("pacman", "zypper"):
        return {"kind": "orphans", "pm": pm}

    if pm == "dnf":
        return {
            "kind": "command",
            "command": ["dnf", "autoremove", "-y"],
            "requires_root": True,
        }

    raise RuntimeError("Unsupported distribution.")


def _list_orphan_packages(pm):
    """Return orphan package names parsed in Python, never via a shell."""
    if pm == "pacman":
        proc = subprocess.run(
            ["pacman", "-Qtdq"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # pacman exits with 1 when there are no orphans
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    if pm == "zypper":
        proc = subprocess.run(
            ["zypper", "--non-interactive", "packages", "--unneeded"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        names = []
        for line in proc.stdout.splitlines():
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 3 or not parts[0].startswith("i"):
                continue
            name = parts[2]
            if name and name not in names:
                names.append(name)
        return names

    return []


def _orphan_remove_command(pm, packages):
    if pm == "pacman":
        return ["pacman", "-Rns", "--noconfirm", "--", *packages]
    if pm == "zypper":
        return ["zypper", "--non-interactive", "remove", "--clean-deps", *packages]
    raise RuntimeError("Unsupported distribution.")
