import subprocess
from core.commands import build_profile_commands

MARKER = "# TuxPulse schedule"

def _build_command(profile_name):
    commands = build_profile_commands(profile_name)
    joined = " && ".join(commands)
    return f"bash -lc '{joined}'"

def _cron_line(profile_name, frequency):
    cmd = _build_command(profile_name)
    if frequency == "daily":
        return f"0 9 * * * {cmd} {MARKER}"
    if frequency == "weekly":
        return f"0 9 * * 1 {cmd} {MARKER}"
    return f"0 9 1 * * {cmd} {MARKER}"

def _get_current_crontab():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout

def get_current_schedule():
    current = _get_current_crontab().strip()
    return current if current else None

def install_schedule(profile_name, frequency):
    current = _get_current_crontab()
    lines = [line for line in current.splitlines() if MARKER not in line]
    lines.append(_cron_line(profile_name, frequency))
    new_data = "\n".join(lines) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_data, text=True, check=False)
    return proc.returncode == 0

def remove_schedule():
    current = _get_current_crontab()
    lines = [line for line in current.splitlines() if MARKER not in line]
    new_data = "\n".join(lines) + ("\n" if lines else "")
    proc = subprocess.run(["crontab", "-"], input=new_data, text=True, check=False)
    return proc.returncode == 0
