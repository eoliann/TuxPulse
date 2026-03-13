import platform
import shutil
import subprocess

def _read_os_release():
    data = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    data[k] = v.strip('"')
    except Exception:
        pass
    return data

def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return r.stdout.strip()
    except Exception:
        return ""

def build_system_summary():
    osr = _read_os_release()
    distro = osr.get("PRETTY_NAME", "Unknown")
    pm = "nala" if shutil.which("nala") else "apt" if shutil.which("apt") else "unknown"

    lines = [
        f"Distribution: {distro}",
        f"System: {platform.system()}",
        f"Kernel: {platform.release()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor() or 'Unknown'}",
        f"Package manager: {pm}",
        f"Flatpak installed: {'Yes' if shutil.which('flatpak') else 'No'}",
        f"Snap installed: {'Yes' if shutil.which('snap') else 'No'}",
    ]

    mem = _run(["free", "-h"])
    if mem:
        lines += ["", "Memory:", mem]

    root_df = _run(["df", "-h", "/"])
    if root_df:
        lines += ["", "Root partition:", root_df]

    return "\n".join(lines)
