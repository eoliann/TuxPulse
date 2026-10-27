#!/usr/bin/env python3
"""
TuxPulse - Services Manager
Gestionare servicii systemd (listare, stare, pornire/oprire/restart/disable)
"""

import subprocess
from typing import List, Dict, Optional
import os

from core.privilege import elevated_command


def list_services(limit: int = 200) -> List[Dict[str, str]]:
    """
    Listează serviciile systemd cu stare curentă.
    Returnează o listă de dicționare compatibilă cu tabela din UI.
    """
    services: List[Dict[str, str]] = []
    
    try:
        # Folosim systemctl list-unit-files + status pentru informații complete
        output = subprocess.check_output(
            ["systemctl", "list-unit-files", "--type=service", "--no-legend"],
            text=True,
            stderr=subprocess.DEVNULL
        )

        count = 0
        for line in output.splitlines():
            if count >= limit:
                break
                
            parts = line.strip().split()
            if len(parts) < 2:
                continue
                
            unit = parts[0]
            state = parts[1]  # enabled / disabled / static / masked etc.

            # Obținem starea reală (running / stopped)
            try:
                status = subprocess.check_output(
                    ["systemctl", "is-active", unit],
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
            except subprocess.CalledProcessError:
                status = "inactive"

            # Mapare stare pentru UI
            if status == "active":
                display_state = "Running"
            elif state in ("disabled", "masked"):
                display_state = "Disabled"
            else:
                display_state = "Stopped"

            services.append({
                "name": unit,
                "state": display_state,
                "enabled": state in ("enabled", "static"),
                "description": ""  # se poate completa ulterior dacă e nevoie
            })
            count += 1

    except Exception as e:
        # Fallback minim dacă systemctl nu funcționează
        print(f"Warning: Could not list services: {e}")
        services.append({
            "name": "systemd-journald.service",
            "state": "Running",
            "enabled": True,
            "description": "Fallback service"
        })

    return services


def _run_elevated(command: List[str]) -> None:
    """Rulează comanda systemctl cu privilegii (pkexec/sudo) și ridică eroare la eșec."""
    elevated = elevated_command(command)
    result = subprocess.run(elevated, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or f'Failed to run: {" ".join(elevated)}')


def set_service_state(service_name: str, desired_state: str) -> bool:
    """
    Schimbă starea unui serviciu (start / stop / restart / disable / enable).
    
    Args:
        service_name: Numele serviciului (ex: "ssh.service")
        desired_state: "Running", "Stopped", "Disabled", "Restart"
    
    Returns:
        True dacă operațiunea a reușit

    Raises:
        RuntimeError: dacă elevarea privilegiilor sau comanda systemctl eșuează,
        pentru ca UI-ul să poată afișa eroarea utilizatorului.
    """
    if desired_state == "Running":
        # enable --now = enable + start, cu o singură cerere de autentificare
        commands = [["systemctl", "enable", "--now", service_name]]
    elif desired_state == "Stopped":
        commands = [["systemctl", "stop", service_name]]
    elif desired_state == "Disabled":
        # disable --now = stop + disable, cu o singură cerere de autentificare
        commands = [["systemctl", "disable", "--now", service_name]]
    elif desired_state == "Restart":
        commands = [["systemctl", "restart", service_name]]
    else:
        raise RuntimeError(f"Unsupported service state: {desired_state}")

    for command in commands:
        _run_elevated(command)
    return True


def get_service_status(service_name: str) -> Dict[str, str]:
    """Returnează informații detaliate despre un serviciu."""
    try:
        active = subprocess.check_output(
            ["systemctl", "is-active", service_name],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()

        enabled = subprocess.check_output(
            ["systemctl", "is-enabled", service_name],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()

        return {
            "name": service_name,
            "active": active,
            "enabled": enabled,
            "state": "Running" if active == "active" else "Stopped"
        }
    except Exception:
        return {
            "name": service_name,
            "active": "unknown",
            "enabled": "unknown",
            "state": "Stopped"
        }