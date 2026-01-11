import os
from datetime import datetime
from typing import Iterable


class AppLogger:
    def __init__(self, app_root: str) -> None:
        self._path = self._resolve_log_path(app_root)

    def _resolve_log_path(self, app_root: str) -> str:
        preferred = os.path.join(app_root, "logs", "app.log")
        try:
            os.makedirs(os.path.dirname(preferred), exist_ok=True)
            with open(preferred, "a", encoding="utf-8"):
                pass
            return preferred
        except OSError:
            fallback_root = os.environ.get("LOCALAPPDATA", app_root)
            fallback = os.path.join(fallback_root, "CmdLauncher", "logs", "app.log")
            os.makedirs(os.path.dirname(fallback), exist_ok=True)
            return fallback

    def log_block(self, lines: Iterable[str]) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] ---\n")
            for line in lines:
                handle.write(line.rstrip("\n") + "\n")
            handle.write("\n")

    def log_command(
        self,
        command_id: str,
        label: str,
        command: str,
        exit_code: int,
        timed_out: bool,
        output: str,
    ) -> None:
        status = "TIMEOUT" if timed_out else f"exit_code={exit_code}"
        lines = [
            f"command_id={command_id}",
            f"label={label}",
            f"command={command}",
            f"status={status}",
            "output:",
            output.rstrip("\n"),
        ]
        self.log_block(lines)
