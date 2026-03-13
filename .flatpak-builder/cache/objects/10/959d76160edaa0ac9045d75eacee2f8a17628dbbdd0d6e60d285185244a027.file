import os
import shutil
import subprocess

def get_root_usage():
    total, used, free = shutil.disk_usage("/")
    gb = 1024 ** 3
    return {
        "total_gb": round(total / gb, 2),
        "used_gb": round(used / gb, 2),
        "free_gb": round(free / gb, 2),
        "used_percent": round((used / total) * 100, 1) if total else 0.0,
    }

def get_home_top_directories(limit=8):
    home = os.path.expanduser("~")
    cmd = f'du -x -d 1 "{home}" 2>/dev/null | sort -hr | head -n {limit + 1}'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    except Exception:
        return []

    result = []
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        size_k = parts[0]
        path = parts[1]
        if path == home:
            continue
        name = os.path.basename(path) or path
        try:
            size_mb = round(int(size_k) / 1024.0, 1)
        except ValueError:
            continue
        result.append({"name": name, "size_mb": size_mb})
    return result[:limit]
