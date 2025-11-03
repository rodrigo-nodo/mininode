# Flujos declarados en Python (versionados). Hoy: p1_upload_v1.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Callable
from . import steps as ST

@dataclass(frozen=True)
class StepSpec:
    name: str
    args: dict = field(default_factory=dict)

STEP_REGISTRY: Dict[str, Callable] = {
    "upload": ST.step_upload,
}

class S:
    @staticmethod
    def upload(**kwargs): return StepSpec("upload", kwargs)

FLOWS: Dict[str, List[StepSpec]] = {
    "p1_upload_v1": [ S.upload() ],
    "p2_upload_opt_v1": [
        S.upload(),
        S.optimize(ops=["deskew","binarize"])
        ],
}
