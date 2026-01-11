import ctypes
import locale
import os
import sys
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from .models import CommandDefinition


class CommandRunner(QObject):
    output_received = Signal(str)
    started = Signal(str)
    finished = Signal(int, bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._stdout_chunks = []
        self._stderr_chunks = []
        self._running = False
        self._command_str = ""
        self._timed_out = False
        self._encoding_override: Optional[str] = None
        self._cmd_prefix = ""
        self._use_cmd_unicode = False
        self._cmd_program = os.environ.get("ComSpec", "cmd.exe")

        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.finished.connect(self._on_finished)
        self._timer.timeout.connect(self._on_timeout)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def command_str(self) -> str:
        return self._command_str

    def start(self, command: CommandDefinition, command_str: str) -> bool:
        if self._running:
            return False

        self._stdout_chunks = []
        self._stderr_chunks = []
        self._command_str = command_str
        self._timed_out = False
        self._running = True

        self._apply_no_window()
        full_command = f"{self._cmd_prefix}{command_str}" if self._cmd_prefix else command_str
        self._process.setProgram(self._cmd_program)
        if self._use_cmd_unicode:
            self._process.setArguments(["/u", "/c", full_command])
        else:
            self._process.setArguments(["/c", full_command])
        self._process.start()
        self.started.emit(command.label)

        if command.timeout > 0:
            self._timer.start(command.timeout * 1000)

        return True

    def start_with_args(self, command: CommandDefinition, program: str, args: list, display: str) -> bool:
        if self._running:
            return False

        self._stdout_chunks = []
        self._stderr_chunks = []
        self._command_str = display
        self._timed_out = False
        self._running = True

        self._apply_no_window()
        self._process.setProgram(program)
        self._process.setArguments(args)
        self._process.start()
        self.started.emit(command.label)

        if command.timeout > 0:
            self._timer.start(command.timeout * 1000)

        return True

    def set_output_encoding(self, encoding: Optional[str]) -> None:
        self._encoding_override = encoding

    def set_cmd_prefix(self, prefix: str) -> None:
        self._cmd_prefix = prefix

    def set_cmd_unicode(self, enabled: bool) -> None:
        self._use_cmd_unicode = enabled

    def launch_admin(self, command_str: str) -> bool:
        self._command_str = command_str
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            self._cmd_program,
            f"/c {command_str}",
            None,
            1,
        )
        return result > 32

    def _read_stdout(self) -> None:
        data = self._process.readAllStandardOutput().data()
        text = self._decode_output(data)
        self._stdout_chunks.append(text)
        self.output_received.emit(text)

    def _read_stderr(self) -> None:
        data = self._process.readAllStandardError().data()
        text = self._decode_output(data)
        self._stderr_chunks.append(text)
        self.output_received.emit(text)

    def _on_timeout(self) -> None:
        if self._running:
            self._timed_out = True
            self._process.kill()

    def _on_finished(self, exit_code: int, _status) -> None:
        self._timer.stop()
        self._running = False
        output = "".join(self._stdout_chunks + self._stderr_chunks)
        self.finished.emit(exit_code, self._timed_out, output)

    def _decode_output(self, data: bytes) -> str:
        if self._encoding_override:
            return data.decode(self._encoding_override, errors="replace")
        if self._looks_like_utf16(data):
            return data.decode("utf-16-le", errors="replace")
        if sys.platform == "win32":
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("gbk", errors="replace")
        return data.decode(locale.getpreferredencoding(False), errors="replace")

    def _looks_like_utf16(self, data: bytes) -> bool:
        if len(data) >= 2 and data[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return True
        if len(data) >= 4 and data[1:4:2] == b"\x00\x00":
            return True
        return False

    def _apply_no_window(self) -> None:
        if sys.platform != "win32":
            return

        if not hasattr(self._process, "setCreateProcessArgumentsModifier"):
            return

        def modifier(args: dict) -> None:
            args["flags"] = args.get("flags", 0) | 0x08000000

        self._process.setCreateProcessArgumentsModifier(modifier)
