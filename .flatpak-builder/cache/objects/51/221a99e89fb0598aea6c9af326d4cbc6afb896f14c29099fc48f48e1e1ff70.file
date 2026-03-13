import platform
import subprocess

def _run_shell(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        return r.stdout.strip()
    except Exception:
        return ""

def get_kernel_report():
    current = platform.release()
    raw = _run_shell("dpkg --list | grep '^ii' | grep 'linux-image' | awk '{print $2}'")
    installed = [line.strip() for line in raw.splitlines() if line.strip()]

    suggested = []
    for pkg in installed:
        if current not in pkg and "generic" in pkg:
            suggested.append(pkg)

    return {
        "current": current,
        "installed": installed,
        "suggested": suggested,
    }

def removal_commands_for_suggested():
    report = get_kernel_report()
    if not report["suggested"]:
        return []
    pkgs = " ".join(report["suggested"])
    return [f"apt remove -y {pkgs}", "apt autoremove -y"]
