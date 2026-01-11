import json
import os
import sys
from typing import List

from .models import CommandDefinition, ParamDefinition


def get_app_root() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _parse_params(raw_params: list) -> List[ParamDefinition]:
    params: List[ParamDefinition] = []
    for item in raw_params:
        params.append(
            ParamDefinition(
                param_id=item["id"],
                label=item.get("label", item["id"]),
                kind=item.get("type", "string"),
                required=bool(item.get("required", False)),
                default=item.get("default"),
                choices=item.get("choices"),
                choice_labels=item.get("labels"),
                ui=item.get("ui"),
                min_value=item.get("min"),
                max_value=item.get("max"),
            )
        )
    return params


def load_commands(app_root: str) -> List[CommandDefinition]:
    config_path = os.path.join(app_root, "config", "commands.json")
    with open(config_path, "r", encoding="utf-8-sig") as handle:
        raw = json.load(handle)

    commands: List[CommandDefinition] = []
    for item in raw.get("commands", []):
        commands.append(
            CommandDefinition(
                command_id=item["id"],
                label=item["label"],
                description=item.get("description", ""),
                kind=item.get("kind", "command"),
                template=item.get("template", ""),
                params=_parse_params(item.get("params", [])),
                timeout=int(item.get("timeout", 10)),
                admin=bool(item.get("admin", False)),
            )
        )

    return commands
