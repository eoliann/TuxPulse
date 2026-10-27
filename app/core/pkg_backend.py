from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

from core.platform import detect_platform


class PackageBackend:
    def __init__(self) -> None:
        self.platform = detect_platform()
        self.pm = self.platform.package_manager
        self.backend_name = self.pm
        self.name = self.pm

    def _run(
        self,
        command: Sequence[str],
        *,
        allow_codes: Sequence[int] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        env = None
        if command and command[0] in {"apt", "apt-get", "dpkg", "dpkg-query"}:
            env = {"DEBIAN_FRONTEND": "noninteractive", **os.environ}
        return subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
            check=False,
        )

    def maintenance_steps(self) -> List[Tuple[str, str]]:
        """Returnează pașii de mentenanță completă pentru managerul de pachete detectat."""
        if self.pm == "apt":
            return [
                ("Update package lists", "apt-get update"),
                ("Upgrade system packages", "apt-get upgrade -y"),
                ("Remove old packages and configs", "apt-get autopurge -y || true"),
                ("Remove unused packages", "apt-get autoremove -y || true"),
                ("Clean package cache", "apt-get autoclean || true"),
            ]

        if self.pm == "dnf":
            return [
                ("Refresh package metadata", "dnf makecache --refresh -y || true"),
                ("Upgrade system packages", "dnf upgrade -y"),
                ("Remove unused dependencies", "dnf autoremove -y || true"),
                ("Clean package cache", "dnf clean all || true"),
            ]

        if self.pm == "pacman":
            return [
                ("Sync repositories and upgrade packages", "pacman -Syu --noconfirm"),
                ("Clean package cache", "pacman -Sc --noconfirm || true"),
            ]

        if self.pm == "zypper":
            return [
                ("Refresh repositories", "zypper --non-interactive refresh || true"),
                ("Upgrade system packages", "zypper --non-interactive update"),
                ("Remove unneeded dependencies", "zypper --non-interactive packages --unneeded || true"),
                ("Clean package cache", "zypper clean --all || true"),
            ]

        return []

    def _parse_name_version_lines(
        self,
        output: str,
        search: str = "",
        limit: Optional[int] = 300,
        *,
        status: str = "installed",
    ) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        needle = search.lower().strip()

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if "\t" in line:
                name, version = line.split("\t", 1)
            else:
                parts = line.split(maxsplit=1)
                name = parts[0]
                version = parts[1] if len(parts) > 1 else ""

            if needle and needle not in name.lower():
                continue

            items.append({"name": name, "version": version, "status": status})

            if limit is not None and len(items) >= limit:
                break

        return items

    def list_installed(self, search: str = "", limit: Optional[int] = 300) -> List[Dict[str, str]]:
        try:
            if self.pm == "apt":
                proc = self._run(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
                if proc.returncode == 0:
                    return self._parse_name_version_lines(proc.stdout, search=search, limit=limit)
                return []

            if self.pm == "pacman":
                proc = self._run(["pacman", "-Q"])
                if proc.returncode == 0:
                    return self._parse_name_version_lines(proc.stdout, search=search, limit=limit)
                return []

            if self.pm in {"dnf", "zypper"}:
                proc = self._run(["rpm", "-qa", "--qf", r"%{NAME}\t%{VERSION}-%{RELEASE}\n"])
                if proc.returncode == 0:
                    return self._parse_name_version_lines(proc.stdout, search=search, limit=limit)
                return []
        except Exception:
            return []

        return []

    def count_installed(self) -> int:
        try:
            if self.pm == "apt":
                proc = self._run(["dpkg-query", "-W", "-f=${Package}\n"])
            elif self.pm == "pacman":
                proc = self._run(["pacman", "-Qq"])
            elif self.pm in {"dnf", "zypper"}:
                proc = self._run(["rpm", "-qa"])
            else:
                return 0

            if proc.returncode != 0:
                return 0
            return sum(1 for line in proc.stdout.splitlines() if line.strip())
        except Exception:
            return 0

    def list_upgradable(self, limit: Optional[int] = 300) -> List[Dict[str, str]]:
        try:
            if self.pm == "apt":
                proc = self._run(["apt", "list", "--upgradable"])
                return self._parse_apt_upgradable(proc.stdout, limit=limit) if proc.returncode == 0 else []

            if self.pm == "pacman":
                proc = self._run(["pacman", "-Qu"])
                return self._parse_pacman_upgradable(proc.stdout, limit=limit) if proc.returncode == 0 else []

            if self.pm == "dnf":
                proc = self._run(["dnf", "-q", "check-update"])
                if proc.returncode not in (0, 100):
                    return []
                return self._parse_dnf_upgradable(proc.stdout, limit=limit)

            if self.pm == "zypper":
                proc = self._run(["zypper", "--non-interactive", "list-updates"])
                return self._parse_zypper_upgradable(proc.stdout, limit=limit) if proc.returncode == 0 else []
        except Exception:
            return []

        return []

    def _parse_apt_upgradable(self, output: str, limit: Optional[int]) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("Listing...") or "/" not in line:
                continue
            parts = line.split()
            name = line.split("/", 1)[0]
            version = parts[1] if len(parts) > 1 else "upgradable"
            items.append({"name": name, "version": version, "status": "upgradable"})
            if limit is not None and len(items) >= limit:
                break
        return items

    def _parse_pacman_upgradable(self, output: str, limit: Optional[int]) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[0]
            version = parts[3]
            items.append({"name": name, "version": version, "status": "upgradable"})
            if limit is not None and len(items) >= limit:
                break
        return items

    def _parse_dnf_upgradable(self, output: str, limit: Optional[int]) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        skip_prefixes = (
            "Last metadata expiration",
            "Obsoleting Packages",
            "Available Upgrades",
            "Security:",
        )
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith(skip_prefixes):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name_arch = parts[0]
            name = name_arch.rsplit(".", 1)[0] if "." in name_arch else name_arch
            version = parts[1]
            items.append({"name": name, "version": version, "status": "upgradable"})
            if limit is not None and len(items) >= limit:
                break
        return items

    def _parse_zypper_upgradable(self, output: str, limit: Optional[int]) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("Loading", "Reading", "Repository", "S |", "--", "No updates")):
                continue
            if "|" not in raw_line:
                continue

            parts = [part.strip() for part in raw_line.split("|")]
            parts = [part for part in parts if part]
            if len(parts) >= 6 and parts[0].lower() in {"v", "s"}:
                name = parts[2]
                version = parts[4]
            elif len(parts) >= 5:
                name = parts[1]
                version = parts[3]
            else:
                continue

            if name.lower() == "name":
                continue

            items.append({"name": name, "version": version, "status": "upgradable"})
            if limit is not None and len(items) >= limit:
                break
        return items

    def remove_cmd(self, name: str) -> List[str]:
        if self.pm == "apt":
            return ["apt-get", "remove", "-y", name]
        if self.pm == "pacman":
            return ["pacman", "-R", "--noconfirm", name]
        if self.pm == "dnf":
            return ["dnf", "remove", "-y", name]
        if self.pm == "zypper":
            return ["zypper", "--non-interactive", "remove", name]
        raise RuntimeError("No supported package manager found.")

    def purge_cmd(self, name: str) -> List[str]:
        if self.pm == "apt":
            return ["apt-get", "purge", "-y", name]
        if self.pm == "pacman":
            return ["pacman", "-Rns", "--noconfirm", name]
        if self.pm == "dnf":
            return ["dnf", "remove", "-y", name]
        if self.pm == "zypper":
            return ["zypper", "--non-interactive", "remove", name]
        raise RuntimeError("No supported package manager found.")

    def has_flatpak(self) -> bool:
        return shutil.which("flatpak") is not None
