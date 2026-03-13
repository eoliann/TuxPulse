from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget, QTabWidget, QSplitter
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import platform

from core.commands import build_actions
from core.i18n import I18N
from core.runner import CommandRunner
from services.disk_analyzer import get_home_top_directories, get_root_usage
from services.kernels import get_kernel_report, removal_commands_for_suggested
from services.monitor import MonitorService
from services.scheduler import install_schedule, remove_schedule, get_current_schedule
from services.systeminfo import build_system_summary


def _get_distribution():
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return platform.system()


class LiveChart(FigureCanvas):
    def __init__(self, title, color):
        self.fig = Figure(facecolor="#0f172a")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#0f172a")
        self.title = title
        self.color = color
        super().__init__(self.fig)

    def update_series(self, values, title=None):
        if title:
            self.title = title
        self.ax.clear()
        self.ax.set_facecolor("#0f172a")
        self.ax.plot(values, linewidth=2.4, color=self.color)
        self.ax.fill_between(range(len(values)), values, color=self.color, alpha=0.28)
        self.ax.set_title(self.title, color="white", fontsize=11)
        self.ax.tick_params(colors="#cbd5e1")
        for spine in self.ax.spines.values():
            spine.set_color("#334155")
        self.ax.grid(True, alpha=0.15)
        self.fig.tight_layout()
        self.draw()


class PieChart(FigureCanvas):
    def __init__(self, title):
        self.fig = Figure(facecolor="#0f172a")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#0f172a")
        self.title = title
        super().__init__(self.fig)

    def update_usage(self, used_gb, free_gb, title=None):
        if title:
            self.title = title
        self.ax.clear()
        self.ax.set_facecolor("#0f172a")
        wedges, texts, autotexts = self.ax.pie(
            [used_gb, free_gb],
            labels=["Used", "Free"],
            autopct="%1.1f%%",
            startangle=90,
            colors=["#ef4444", "#22c55e"],
            wedgeprops={"linewidth": 1, "edgecolor": "#0f172a"}
        )
        for t in texts + autotexts:
            t.set_color("white")
        self.ax.set_title(self.title, color="white", fontsize=11)
        self.fig.tight_layout()
        self.draw()


class BarChart(FigureCanvas):
    def __init__(self, title):
        self.fig = Figure(facecolor="#0f172a")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#0f172a")
        self.title = title
        super().__init__(self.fig)

    def update_bars(self, labels, values, title=None):
        if title:
            self.title = title
        self.ax.clear()
        self.ax.set_facecolor("#0f172a")
        self.ax.bar(labels, values, color="#8b5cf6")
        self.ax.set_title(self.title, color="white", fontsize=11)
        self.ax.tick_params(axis="x", colors="#cbd5e1", rotation=25)
        self.ax.tick_params(axis="y", colors="#cbd5e1")
        for spine in self.ax.spines.values():
            spine.set_color("#334155")
        self.ax.grid(True, axis="y", alpha=0.15)
        self.fig.tight_layout()
        self.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18N("en")
        self.actions = build_actions()
        self.runner = CommandRunner(self.append_log)
        self.monitor = MonitorService(history=40)

        self.setWindowTitle(self.i18n.t("app_title"))
        self.resize(1320, 820)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # Left panel
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        self.title_label = QLabel()
        self.title_label.setObjectName("Title")

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("Subtitle")
        self.subtitle_label.setWordWrap(True)

        self.distribution_label = QLabel()
        self.distribution_label.setObjectName("SectionTitle")

        language_row = QHBoxLayout()
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Română", "ro")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)

        self.actions_label = QLabel()
        self.actions_label.setObjectName("SectionTitle")

        self.action_list = QListWidget()
        self.action_list.setObjectName("ActionList")

        self.run_btn = QPushButton()
        self.run_btn.clicked.connect(self.run_selected_action)

        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh_all)

        sidebar_layout.addWidget(self.title_label)
        sidebar_layout.addWidget(self.subtitle_label)
        sidebar_layout.addWidget(self.distribution_label)
        sidebar_layout.addLayout(language_row)
        sidebar_layout.addWidget(self.actions_label)
        sidebar_layout.addWidget(self.action_list, 1)
        sidebar_layout.addWidget(self.run_btn)
        sidebar_layout.addWidget(self.refresh_btn)

        # Right panel
        self.panel = QFrame()
        self.panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("Tabs")

        # Dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_tab)

        self.info_title = QLabel()
        self.info_title.setObjectName("SectionTitle")
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)

        self.log_title = QLabel()
        self.log_title.setObjectName("SectionTitle")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        self.cpu_chart = LiveChart("", "#3b82f6")
        self.ram_chart = LiveChart("", "#22c55e")
        self.disk_chart = LiveChart("", "#f59e0b")
        self.net_chart = LiveChart("", "#ec4899")

        info_section = QWidget()
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)
        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_box)

        graphs_section = QWidget()
        graphs_layout = QVBoxLayout(graphs_section)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        graphs_layout.setSpacing(8)
        graph_row_1 = QHBoxLayout()
        graph_row_2 = QHBoxLayout()
        graph_row_1.addWidget(self.cpu_chart)
        graph_row_1.addWidget(self.ram_chart)
        graph_row_2.addWidget(self.disk_chart)
        graph_row_2.addWidget(self.net_chart)
        graphs_layout.addLayout(graph_row_1)
        graphs_layout.addLayout(graph_row_2)

        log_section = QWidget()
        log_layout = QVBoxLayout(log_section)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)
        log_layout.addWidget(self.log_title)
        log_layout.addWidget(self.log_box)

        self.dashboard_splitter = QSplitter(Qt.Vertical)
        self.dashboard_splitter.addWidget(info_section)
        self.dashboard_splitter.addWidget(graphs_section)
        self.dashboard_splitter.addWidget(log_section)
        self.dashboard_splitter.setStretchFactor(0, 2)
        self.dashboard_splitter.setStretchFactor(1, 4)
        self.dashboard_splitter.setStretchFactor(2, 2)

        dashboard_layout.addWidget(self.dashboard_splitter)

        # Disk tab
        disk_tab = QWidget()
        disk_layout = QVBoxLayout(disk_tab)
        self.disk_partition_title = QLabel()
        self.disk_partition_title.setObjectName("SectionTitle")
        self.disk_pie = PieChart("")
        self.disk_dirs_title = QLabel()
        self.disk_dirs_title.setObjectName("SectionTitle")
        self.disk_bar = BarChart("")
        self.disk_analyze_btn = QPushButton()
        self.disk_analyze_btn.clicked.connect(self.refresh_disk_analysis)
        disk_layout.addWidget(self.disk_partition_title)
        disk_layout.addWidget(self.disk_pie, 2)
        disk_layout.addWidget(self.disk_dirs_title)
        disk_layout.addWidget(self.disk_bar, 2)
        disk_layout.addWidget(self.disk_analyze_btn)

        # Kernel tab
        kernel_tab = QWidget()
        kernel_layout = QVBoxLayout(kernel_tab)
        self.kernel_title = QLabel()
        self.kernel_title.setObjectName("SectionTitle")
        self.kernel_text = QTextEdit()
        self.kernel_text.setReadOnly(True)
        self.kernel_analyze_btn = QPushButton()
        self.kernel_analyze_btn.clicked.connect(self.refresh_kernel_analysis)
        self.kernel_remove_btn = QPushButton()
        self.kernel_remove_btn.clicked.connect(self.remove_old_kernels)
        kernel_layout.addWidget(self.kernel_title)
        kernel_layout.addWidget(self.kernel_text, 1)
        kernel_layout.addWidget(self.kernel_analyze_btn)
        kernel_layout.addWidget(self.kernel_remove_btn)

        # Scheduler tab
        scheduler_tab = QWidget()
        scheduler_layout = QVBoxLayout(scheduler_tab)
        self.scheduler_title = QLabel()
        self.scheduler_title.setObjectName("SectionTitle")

        profile_row = QHBoxLayout()
        self.profile_label = QLabel()
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("", "quick")
        self.profile_combo.addItem("", "full")

        frequency_row = QHBoxLayout()
        self.frequency_label = QLabel()
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItem("", "daily")
        self.frequency_combo.addItem("", "weekly")
        self.frequency_combo.addItem("", "monthly")

        profile_row.addWidget(self.profile_label)
        profile_row.addWidget(self.profile_combo)
        frequency_row.addWidget(self.frequency_label)
        frequency_row.addWidget(self.frequency_combo)

        self.scheduler_info = QTextEdit()
        self.scheduler_info.setReadOnly(True)
        self.scheduler_install_btn = QPushButton()
        self.scheduler_install_btn.clicked.connect(self.install_schedule_clicked)
        self.scheduler_remove_btn = QPushButton()
        self.scheduler_remove_btn.clicked.connect(self.remove_schedule_clicked)

        scheduler_layout.addWidget(self.scheduler_title)
        scheduler_layout.addLayout(profile_row)
        scheduler_layout.addLayout(frequency_row)
        scheduler_layout.addWidget(self.scheduler_info, 1)
        scheduler_layout.addWidget(self.scheduler_install_btn)
        scheduler_layout.addWidget(self.scheduler_remove_btn)

        self.tabs.addTab(dashboard_tab, "")
        self.tabs.addTab(disk_tab, "")
        self.tabs.addTab(kernel_tab, "")
        self.tabs.addTab(scheduler_tab, "")

        panel_layout.addWidget(self.tabs)

        root.addWidget(self.sidebar, 3)
        root.addWidget(self.panel, 6)

        self.apply_style()
        self.update_action_list()
        self.retranslate_ui()
        self.refresh_all()
        self.append_log(self.i18n.t("info_started"))

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_monitoring)
        self.timer.start(1000)
        self.update_monitoring()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background: #0f172a;
                color: #e5e7eb;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 13px;
            }
            QFrame#Sidebar, QFrame#Panel {
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 14px;
            }
            QLabel#Title {
                font-size: 28px;
                font-weight: bold;
                color: #f8fafc;
            }
            QLabel#Subtitle {
                color: #94a3b8;
            }
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: bold;
                color: #f8fafc;
            }
            QListWidget, QTextEdit, QTabWidget::pane {
                background: #0b1220;
                border: 1px solid #243041;
                border-radius: 10px;
                padding: 8px;
            }
            QComboBox {
                background-color: #0b1220;
                color: #e5e7eb;
                border: 1px solid #243041;
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #0b1220;
                color: #e5e7eb;
                selection-background-color: #2563eb;
                border: 1px solid #243041;
                outline: 0;
            }
            QSplitter::handle {
                background: #243041;
            }
            QListWidget::item {
                padding: 10px;
                margin: 3px 0;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background: #2563eb;
                color: white;
            }
            QTabBar::tab {
                background: #0b1220;
                border: 1px solid #243041;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 14px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #2563eb;
                color: white;
            }
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                min-height: 40px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)

    def change_language(self):
        lang = self.language_combo.currentData()
        self.i18n.set_lang(lang)
        self.retranslate_ui()
        self.update_action_list()
        self.refresh_kernel_analysis()
        self.refresh_disk_analysis()

    def retranslate_ui(self):
        self.setWindowTitle(self.i18n.t("app_title"))
        self.title_label.setText(self.i18n.t("app_name"))
        self.subtitle_label.setText(self.i18n.t("subtitle"))
        self.distribution_label.setText(f"{self.i18n.t('distribution')}: {_get_distribution()}")
        self.language_label.setText(self.i18n.t("language"))
        self.actions_label.setText(self.i18n.t("system_actions"))
        self.run_btn.setText(self.i18n.t("run_action"))
        self.refresh_btn.setText(self.i18n.t("refresh"))
        self.info_title.setText(self.i18n.t("system_info"))
        self.log_title.setText(self.i18n.t("execution_log"))
        self.disk_partition_title.setText(self.i18n.t("disk_partition_usage"))
        self.disk_dirs_title.setText(self.i18n.t("largest_directories"))
        self.disk_analyze_btn.setText(self.i18n.t("analyze_disk"))
        self.kernel_title.setText(self.i18n.t("kernel_tools"))
        self.kernel_analyze_btn.setText(self.i18n.t("analyze_kernels"))
        self.kernel_remove_btn.setText(self.i18n.t("remove_old_kernels"))
        self.scheduler_title.setText(self.i18n.t("scheduler"))
        self.profile_label.setText(self.i18n.t("schedule_profile"))
        self.frequency_label.setText(self.i18n.t("schedule_frequency"))
        self.scheduler_install_btn.setText(self.i18n.t("install_schedule"))
        self.scheduler_remove_btn.setText(self.i18n.t("remove_schedule"))
        self.profile_combo.setItemText(0, self.i18n.t("quick_profile"))
        self.profile_combo.setItemText(1, self.i18n.t("full_profile"))
        self.frequency_combo.setItemText(0, self.i18n.t("daily"))
        self.frequency_combo.setItemText(1, self.i18n.t("weekly"))
        self.frequency_combo.setItemText(2, self.i18n.t("monthly"))
        self.tabs.setTabText(0, self.i18n.t("dashboard"))
        self.tabs.setTabText(1, self.i18n.t("disk_analysis"))
        self.tabs.setTabText(2, self.i18n.t("kernel_tools"))
        self.tabs.setTabText(3, self.i18n.t("scheduler"))
        current_schedule = get_current_schedule()
        if current_schedule:
            self.scheduler_info.setPlainText(
                f"{self.i18n.t('installed_scheduler')}:\n\n{current_schedule}"
            )
        else:
            self.scheduler_info.setPlainText(
                f"{self.i18n.t('no_scheduler')}\n\n{self.i18n.t('no_scheduler_details')}"
            )

    def update_action_list(self):
        current_row = self.action_list.currentRow()
        self.action_list.clear()
        for action in self.actions:
            label = action["label_en"] if self.i18n.lang == "en" else action["label_ro"]
            description = action["description_en"] if self.i18n.lang == "en" else action["description_ro"]
            item = QListWidgetItem(label)
            item.setToolTip(description)
            self.action_list.addItem(item)
        if self.action_list.count() > 0:
            self.action_list.setCurrentRow(max(0, current_row))

    def append_log(self, text):
        cursor = self.log_box.textCursor()
        cursor.movePosition(cursor.End)
        self.log_box.setTextCursor(cursor)
        self.log_box.insertPlainText(text + ("\n" if not text.endswith("\n") else ""))

    def refresh_all(self):
        self.info_box.setPlainText(build_system_summary())
        self.refresh_disk_analysis()
        self.refresh_kernel_analysis()
        self.retranslate_ui()
        self.append_log(self.i18n.t("info_refreshed"))

    def run_selected_action(self):
        row = self.action_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", self.i18n.t("warning_select_action"))
            return
        action = self.actions[row]
        label = action["label_en"] if self.i18n.lang == "en" else action["label_ro"]
        description = action["description_en"] if self.i18n.lang == "en" else action["description_ro"]
        self.append_log(f"\n=== {label} ===")
        self.append_log(description)
        code = self.runner.run(action["commands"], requires_root=action.get("root", True))
        if code != 0:
            QMessageBox.critical(self, "Error", f"{self.i18n.t('action_failed')} {code}")
        self.refresh_all()

    def update_monitoring(self):
        data = self.monitor.snapshot()
        self.cpu_chart.update_series(data["cpu_history"], self.i18n.t("cpu_usage"))
        self.ram_chart.update_series(data["ram_history"], self.i18n.t("ram_usage"))
        self.disk_chart.update_series(data["disk_history"], self.i18n.t("disk_usage"))
        self.net_chart.update_series(data["net_history"], self.i18n.t("network_usage"))

    def refresh_disk_analysis(self):
        usage = get_root_usage()
        self.disk_pie.update_usage(usage["used_gb"], usage["free_gb"], self.i18n.t("disk_partition_usage"))
        dirs = get_home_top_directories()
        labels = [d["name"] for d in dirs] if dirs else ["N/A"]
        values = [d["size_mb"] for d in dirs] if dirs else [0]
        self.disk_bar.update_bars(labels, values, self.i18n.t("largest_directories"))

    def refresh_kernel_analysis(self):
        report = get_kernel_report()
        lines = [
            f"{self.i18n.t('current_kernel')}: {report['current']}",
            "",
            f"{self.i18n.t('installed_kernels')}:",
        ]
        lines.extend(report["installed"] or ["-"])
        lines += ["", f"{self.i18n.t('suggested_old_kernels')}:"]
        lines.extend(report["suggested"] or ["-"])
        self.kernel_text.setPlainText("\n".join(lines))

    def remove_old_kernels(self):
        commands = removal_commands_for_suggested()
        if not commands:
            QMessageBox.information(self, "Info", self.i18n.t("no_old_kernels"))
            return
        answer = QMessageBox.question(
            self,
            "Confirm",
            self.i18n.t("confirm_remove_kernels"),
            QMessageBox.Yes | QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        self.append_log("\n=== Kernel cleanup ===")
        code = self.runner.run(commands, requires_root=True)
        if code != 0:
            QMessageBox.critical(self, "Error", f"{self.i18n.t('action_failed')} {code}")
        self.refresh_kernel_analysis()

    def install_schedule_clicked(self):
        profile = self.profile_combo.currentData()
        frequency = self.frequency_combo.currentData()
        ok = install_schedule(profile, frequency)
        if ok:
            self.retranslate_ui()
            QMessageBox.information(self, "Info", self.i18n.t("schedule_installed"))
        else:
            QMessageBox.critical(self, "Error", self.i18n.t("schedule_failed"))

    def remove_schedule_clicked(self):
        ok = remove_schedule()
        if ok:
            self.retranslate_ui()
            QMessageBox.information(self, "Info", self.i18n.t("schedule_removed"))
        else:
            QMessageBox.critical(self, "Error", self.i18n.t("schedule_failed"))
