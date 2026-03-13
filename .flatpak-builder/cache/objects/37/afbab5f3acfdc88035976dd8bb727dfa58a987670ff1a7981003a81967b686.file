import subprocess

class CommandRunner:
    def __init__(self, logger):
        self.logger = logger

    def run(self, commands, requires_root=True):
        if not commands:
            self.logger("[INFO] No commands to execute.")
            return 0

        script = "set -e\n" + "\n".join(commands) + "\n"
        cmd = ["pkexec", "bash", "-lc", script] if requires_root else ["bash", "-lc", script]

        self.logger("$ " + " ".join(cmd))
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except Exception as exc:
            self.logger(f"[ERROR] {exc}")
            return 1

        if process.stdout is not None:
            for line in process.stdout:
                self.logger(line.rstrip())
        return process.wait()
