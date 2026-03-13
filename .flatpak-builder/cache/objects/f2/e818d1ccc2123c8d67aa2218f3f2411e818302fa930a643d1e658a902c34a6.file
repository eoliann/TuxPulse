import shutil

def has_cmd(name):
    return shutil.which(name) is not None

def detect_pm():
    if has_cmd("nala"):
        return "nala"
    if has_cmd("apt"):
        return "apt"
    return None

def build_actions():
    pm = detect_pm()
    actions = []

    if pm == "nala":
        actions.extend([
            {
                "id": "system_update",
                "label_en": "System update",
                "label_ro": "Actualizare sistem",
                "description_en": "Run nala update and nala full-upgrade.",
                "description_ro": "Rulează nala update și nala full-upgrade.",
                "commands": ["nala update", "nala full-upgrade -y"],
                "root": True,
            },
            {
                "id": "system_cleanup",
                "label_en": "System cleanup",
                "label_ro": "Curățare sistem",
                "description_en": "Run nala autoremove and nala clean.",
                "description_ro": "Rulează nala autoremove și nala clean.",
                "commands": ["nala autoremove -y", "nala clean"],
                "root": True,
            },
        ])
    elif pm == "apt":
        actions.extend([
            {
                "id": "system_update",
                "label_en": "System update",
                "label_ro": "Actualizare sistem",
                "description_en": "Run apt update and apt full-upgrade.",
                "description_ro": "Rulează apt update și apt full-upgrade.",
                "commands": ["apt update", "apt full-upgrade -y"],
                "root": True,
            },
            {
                "id": "system_cleanup",
                "label_en": "System cleanup",
                "label_ro": "Curățare sistem",
                "description_en": "Run apt autoremove and apt autoclean.",
                "description_ro": "Rulează apt autoremove și apt autoclean.",
                "commands": ["apt autoremove -y", "apt autoclean -y"],
                "root": True,
            },
        ])

    if has_cmd("flatpak"):
        actions.append({
            "id": "flatpak_update",
            "label_en": "Update Flatpak packages",
            "label_ro": "Actualizare pachete Flatpak",
            "description_en": "Update installed Flatpak applications.",
            "description_ro": "Actualizează aplicațiile Flatpak instalate.",
            "commands": ["flatpak update -y"],
            "root": True,
        })

    actions.extend([
        {
            "id": "systemd_logs",
            "label_en": "Clean systemd logs",
            "label_ro": "Curățare loguri systemd",
            "description_en": "Reduce systemd journal size to 7 days and 100 MB.",
            "description_ro": "Reduce dimensiunea jurnalului systemd la 7 zile și 100 MB.",
            "commands": ["journalctl --vacuum-time=7d", "journalctl --vacuum-size=100M"],
            "root": True,
        },
        {
            "id": "thumbnails",
            "label_en": "Clean thumbnails",
            "label_ro": "Curățare thumbnails",
            "description_en": "Delete the current user's thumbnail cache.",
            "description_ro": "Șterge cache-ul de miniaturi al utilizatorului curent.",
            "commands": ['rm -rf "$HOME/.cache/thumbnails/"*'],
            "root": False,
        },
        {
            "id": "disk_usage_text",
            "label_en": "Check disk space",
            "label_ro": "Verificare spațiu disc",
            "description_en": "Show disk usage in the execution log.",
            "description_ro": "Afișează utilizarea discului în jurnalul de execuție.",
            "commands": ["df -h"],
            "root": False,
        },
    ])
    return actions

def build_profile_commands(profile_name="quick"):
    pm = detect_pm()
    cmds = []
    if pm == "nala":
        cmds += ["nala update", "nala full-upgrade -y", "nala autoremove -y", "nala clean"]
    elif pm == "apt":
        cmds += ["apt update", "apt full-upgrade -y", "apt autoremove -y", "apt autoclean -y"]
    if has_cmd("flatpak"):
        cmds += ["flatpak update -y"]
    cmds += ["journalctl --vacuum-time=7d", "journalctl --vacuum-size=100M"]
    if profile_name == "full":
        cmds += ['rm -rf "$HOME/.cache/thumbnails/"*']
    return cmds
