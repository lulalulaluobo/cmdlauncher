from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ParamDefinition:
    param_id: str
    label: str
    kind: str
    required: bool
    default: Optional[str]
    choices: Optional[List[str]]
    choice_labels: Optional[Dict[str, str]]
    ui: Optional[str]
    min_value: Optional[int]
    max_value: Optional[int]


@dataclass(frozen=True)
class CommandDefinition:
    command_id: str
    label: str
    description: str
    kind: str
    template: str
    params: List[ParamDefinition]
    timeout: int
    admin: bool
