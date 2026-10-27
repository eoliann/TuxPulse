import shlex
import subprocess

from core.privilege import elevated_command


class CommandRunner:
    def __init__(self, log_callback):
        self.log_callback = log_callback

    def run(self, commands, requires_root=True):
        last_code = 0
        for cmd in commands:
            if isinstance(cmd, str):
                command = shlex.split(cmd)
            else:
                command = list(cmd)

            try:
                if requires_root:
                    command = elevated_command(command)
            except RuntimeError as exc:
                self.log_callback(str(exc))
                return 127

            self.log_callback('>>> ' + ' '.join(command))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if process.stdout is not None:
                for line in process.stdout:
                    self.log_callback(line.rstrip())
            last_code = process.wait()
            if last_code != 0:
                return last_code
        return last_code
