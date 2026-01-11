from datetime import datetime
import ctypes
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QGridLayout,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from core.command_runner import CommandRunner
from core.logger import AppLogger
from core.models import CommandDefinition, ParamDefinition
from ui.param_dialog import ParamDialog
from ui.wifi_select_dialog import WifiSelectDialog


class MainWindow(QMainWindow):
    def __init__(self, commands: List[CommandDefinition], logger: AppLogger, app_root: str) -> None:
        super().__init__()
        self._commands = commands
        self._logger = logger
        self._app_root = app_root
        self._command_map: Dict[str, CommandDefinition] = {}
        self._current_command: Optional[CommandDefinition] = None
        self._allow_close = False
        self._command_buttons: List[QPushButton] = []
        self._last_wifi_name: Optional[str] = None

        self.setWindowTitle("CMD不用记   B站：噜啦噜啦萝卜")
        self.setWindowIcon(QIcon(f"{self._app_root}/assets/command.ico"))
        self.resize(900, 600)

        container = QWidget(self)
        layout = QVBoxLayout(container)

        content = QWidget(self)
        content_layout = QHBoxLayout(content)

        self._command_column = QWidget(self)
        self._command_layout = QGridLayout()
        self._command_column.setLayout(self._command_layout)

        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)

        self._bottom_bar = QWidget(self)
        self._bottom_layout = QHBoxLayout()
        self._bottom_bar.setLayout(self._bottom_layout)

        self._clear_button = QPushButton("清空输出", self)
        self._clear_button.clicked.connect(self._clear_output)
        self._bottom_layout.addStretch(1)
        self._bottom_layout.addWidget(self._clear_button)

        content_layout.addWidget(self._command_column, 3)
        content_layout.addWidget(self._output, 4)

        layout.addWidget(content, 1)
        layout.addWidget(self._bottom_bar)
        container.setLayout(layout)

        self.setCentralWidget(container)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)

        self._runner = CommandRunner(self)
        self._runner.output_received.connect(self._on_output)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)

        self._build_buttons()
        self._build_tray()

    def _build_buttons(self) -> None:
        header_cmd = QLabel("Cmd 命令", self)
        header_desc = QLabel("命令说明", self)
        header_cmd.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_desc.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_font = header_cmd.font()
        header_font.setBold(True)
        header_cmd.setFont(header_font)
        header_desc.setFont(header_font)
        self._command_layout.addWidget(header_cmd, 0, 0)
        self._command_layout.addWidget(header_desc, 0, 1)

        row = 1
        group_colors = ["#f2f6ff", "#f2fff5", "#fff6f2"]
        group_index = 0
        current_group_color = group_colors[group_index]
        for command in self._commands:
            if command.kind == "group":
                line = QFrame(self)
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                self._command_layout.addWidget(line, row, 0, 1, 2)
                row += 1
                header = QLabel(command.label, self)
                header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                current_group_color = group_colors[group_index]
                header.setStyleSheet(f"background-color: {current_group_color}; padding: 4px 6px;")
                group_font = header.font()
                group_font.setBold(True)
                header.setFont(group_font)
                self._command_layout.addWidget(header, row, 0, 1, 2)
                row += 1
                group_index = (group_index + 1) % len(group_colors)
                continue
            button = QPushButton(command.label, self)
            button.setStyleSheet(
                f"text-align: left; padding: 4px 8px; background: {current_group_color}; "
                "border: 1px solid #d6d6d6; border-radius: 6px;"
            )
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(6)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 40))
            button.setGraphicsEffect(shadow)
            button.clicked.connect(lambda checked=False, cmd=command: self._run_command(cmd))
            self._command_layout.addWidget(button, row, 0)
            desc = QLabel(command.description or "", self)
            desc.setStyleSheet(f"background-color: {current_group_color}; padding: 2px 6px;")
            self._command_layout.addWidget(desc, row, 1)
            self._command_map[command.command_id] = command
            self._command_buttons.append(button)
            row += 1

        self._command_layout.setColumnStretch(0, 1)
        self._command_layout.setColumnStretch(1, 2)
        self._command_layout.setRowStretch(row, 1)
        self._command_layout.setHorizontalSpacing(12)
        self._command_layout.setVerticalSpacing(6)

    def _build_tray(self) -> None:
        icon = QIcon(f"{self._app_root}/assets/command.ico")
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(icon, self)

        menu = QMenu(self)
        show_action = menu.addAction("Show")
        restart_action = menu.addAction("Restart")
        encoding_menu = menu.addMenu("输出编码")
        exit_action = menu.addAction("Exit")
        show_action.triggered.connect(self._show_window)
        restart_action.triggered.connect(self._restart_app)
        exit_action.triggered.connect(self._exit_app)

        encoding_group = QActionGroup(self)
        encoding_group.setExclusive(True)
        auto_action = QAction("自动", self, checkable=True)
        utf8_action = QAction("UTF-8", self, checkable=True)
        encoding_group.addAction(auto_action)
        encoding_group.addAction(utf8_action)
        encoding_menu.addAction(auto_action)
        encoding_menu.addAction(utf8_action)
        auto_action.setChecked(True)
        auto_action.triggered.connect(lambda: self._set_output_encoding("auto"))
        utf8_action.triggered.connect(lambda: self._set_output_encoding("utf8"))

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _exit_app(self) -> None:
        self._allow_close = True
        self._tray.hide()
        self.close()
        QApplication.instance().quit()

    def _restart_app(self) -> None:
        self._allow_close = True
        self._tray.hide()
        QApplication.instance().exit(1000)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def closeEvent(self, event) -> None:
        if self._allow_close:
            event.accept()
        else:
            self.hide()
            event.ignore()

    def _run_command(self, command: CommandDefinition) -> None:
        if self._runner.is_running:
            QMessageBox.information(self, "CmdLauncher", "Command is already running.")
            return

        if command.command_id == "boot_to_bios":
            reply = QMessageBox.warning(
                self,
                "CmdLauncher",
                "该操作将重启并进入 BIOS。\n不懂 BIOS 的伙伴勿点。\n\n继续执行吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        if command.admin and not self._is_admin():
            reply = QMessageBox.warning(
                self,
                "CmdLauncher",
                "该命令需要管理员权限。\n是否以管理员身份重启程序？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._restart_as_admin()
            return

        command_str = self._build_command_string(command)
        if command_str is None:
            return
        command_str = self._expand_env_vars(command_str)

        self._current_command = command
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_output(f"[{timestamp}] RUN {command.label}: {command_str}\n")
        self._set_buttons_enabled(False)

        if command.command_id == "clean_temp":
            program = "powershell"
            args = [
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "$items = Get-ChildItem -LiteralPath $env:TEMP -Force -ErrorAction SilentlyContinue; "
                "$count = $items.Count; "
                "$items | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue; "
                "Write-Output \"Deleted $count items from $env:TEMP\"",
            ]
            started = self._runner.start_with_args(command, program, args, command_str)
        elif command.admin:
            program = "powershell"
            args = ["-NoProfile", "-WindowStyle", "Hidden", "-Command", command_str]
            started = self._runner.start_with_args(command, program, args, command_str)
        else:
            started = self._runner.start(command, command_str)
        if not started:
            self._set_buttons_enabled(True)

    def _build_command_string(self, command: CommandDefinition) -> Optional[str]:
        if command.command_id == "wifi_profile_detail":
            wifi_name = self._select_wifi_profile()
            if not wifi_name:
                return None
            self._last_wifi_name = wifi_name
            return command.template.format(wifi_name=wifi_name)

        if not command.params:
            return command.template

        dialog = ParamDialog(command.label, command.params, self)
        if dialog.exec() != QDialog.Accepted:
            return None

        values = dialog.values()
        resolved = self._resolve_param_values(command.params, values)
        try:
            return command.template.format(**resolved)
        except KeyError as exc:
            QMessageBox.warning(self, "CmdLauncher", f"Missing parameter: {exc}")
            return None

    def _resolve_param_values(
        self, params: List[ParamDefinition], values: Dict[str, str]
    ) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        for param in params:
            value = values.get(param.param_id, "")
            if not value and param.default is not None:
                value = str(param.default)
            resolved[param.param_id] = value
        return resolved

    def _expand_env_vars(self, command_str: str) -> str:
        def replace(match: re.Match) -> str:
            name = match.group(1)
            return os.environ.get(name, match.group(0))

        return re.sub(r"%([A-Za-z0-9_]+)%", replace, command_str)

    def _on_started(self, label: str) -> None:
        self._status.showMessage(f"Running: {label}")

    def _on_output(self, text: str) -> None:
        self._append_output(text)

    def _on_finished(self, exit_code: int, timed_out: bool, output: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "TIMEOUT" if timed_out else f"exit_code={exit_code}"
        if self._current_command and self._current_command.command_id == "wifi_profile_detail":
            wifi_name = self._last_wifi_name or ""
            wifi_password = self._extract_wifi_password(output) or "未找到"
            self._append_output(f"\nWiFi名: {wifi_name}\nWiFi密码: {wifi_password}\n")
        self._append_output(f"\n[{timestamp}] DONE {status}\n")
        self._status.showMessage("Done")
        self._set_buttons_enabled(True)

        if self._current_command:
            self._logger.log_command(
                self._current_command.command_id,
                self._current_command.label,
                self._runner.command_str,
                exit_code,
                timed_out,
                output,
            )

    def _append_output(self, text: str) -> None:
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _clear_output(self) -> None:
        self._output.clear()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in self._command_buttons:
            button.setEnabled(enabled)

    def _select_wifi_profile(self) -> Optional[str]:
        profiles = self._fetch_wifi_profiles()
        if not profiles:
            QMessageBox.information(self, "CmdLauncher", "未找到 WiFi 配置文件。")
            return None
        dialog = WifiSelectDialog(profiles, self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.selected()

    def _fetch_wifi_profiles(self) -> List[str]:
        process = QProcess(self)
        process.setProgram(os.environ.get("ComSpec", "cmd.exe"))
        process.setArguments(["/c", "netsh wlan show profiles"])
        process.start()
        if not process.waitForFinished(5000):
            process.kill()
            return []
        output = process.readAllStandardOutput().data() + process.readAllStandardError().data()
        text = self._decode_output(output)
        profiles: List[str] = []
        for line in text.splitlines():
            match = re.search(r"^(?:\s*)(所有用户配置文件|All User Profile)\s*:\s*(.+)$", line)
            if match:
                name = match.group(2).strip()
                if name and name not in profiles:
                    profiles.append(name)
        return profiles

    def _extract_wifi_password(self, output: str) -> Optional[str]:
        for line in output.splitlines():
            match = re.search(r"^(?:\s*)(关键内容|Key Content)\s*:\s*(.+)$", line)
            if match:
                return match.group(2).strip()
        return None

    def _decode_output(self, data: bytes) -> str:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("gbk", errors="replace")

    def _set_output_encoding(self, mode: str) -> None:
        if mode == "utf8":
            self._runner.set_output_encoding("utf-8")
            self._runner.set_cmd_prefix("chcp 65001 > nul & ")
            self._runner.set_cmd_unicode(False)
            self._status.showMessage("输出编码：UTF-8")
        else:
            self._runner.set_output_encoding(None)
            self._runner.set_cmd_prefix("")
            self._runner.set_cmd_unicode(False)
            self._status.showMessage("输出编码：自动")

    def _is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _restart_as_admin(self) -> None:
        args = sys.argv
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = subprocess.list2cmdline(args[1:])
        else:
            exe = sys.executable
            params = subprocess.list2cmdline(args)
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe,
            params,
            None,
            1,
        )
        if result > 32:
            QApplication.instance().quit()
