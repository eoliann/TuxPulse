import psutil
from collections import deque

class MonitorService:
    def __init__(self, history=40):
        self.cpu_history = deque([0.0] * history, maxlen=history)
        self.ram_history = deque([0.0] * history, maxlen=history)
        self.disk_history = deque([0.0] * history, maxlen=history)
        self.net_history = deque([0.0] * history, maxlen=history)
        self._last_net = psutil.net_io_counters()

    def snapshot(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        current_net = psutil.net_io_counters()
        total_bytes = (current_net.bytes_recv - self._last_net.bytes_recv) + (current_net.bytes_sent - self._last_net.bytes_sent)
        total_kb = total_bytes / 1024.0
        self._last_net = current_net

        self.cpu_history.append(cpu)
        self.ram_history.append(ram)
        self.disk_history.append(disk)
        self.net_history.append(total_kb)

        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "net_kb": total_kb,
            "cpu_history": list(self.cpu_history),
            "ram_history": list(self.ram_history),
            "disk_history": list(self.disk_history),
            "net_history": list(self.net_history),
        }
