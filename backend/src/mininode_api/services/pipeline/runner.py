# Orquestador común. Ejecuta steps de un flow y mide tiempos.
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .flows import FLOWS, STEP_REGISTRY, StepSpec

def execute_flow(flow_name: str, *, ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if flow_name not in FLOWS:
        raise ValueError(f"Flow desconocido: {flow_name}")
    steps = FLOWS[flow_name]
    steps_out: List[Dict[str, Any]] = []
    last_data: Dict[str, Any] = {}

    for spec in steps:
        fn = STEP_REGISTRY.get(spec.name)
        if fn is None:
            steps_out.append({"name": spec.name, "ok": False, "time_ms": 0,
                              "error": {"code":"UNKNOWN_STEP","message":spec.name}})
            break
        try:
            data, t_ms = fn(ctx, spec.args or {})
            steps_out.append({"name": spec.name, "ok": True, "time_ms": t_ms, "data": data})
            last_data = data
            if isinstance(data, dict):
                ctx.update(data) 
        except Exception as e:
            steps_out.append({"name": spec.name, "ok": False, "time_ms": 0,
                              "error": {"code":"STEP_ERROR","message": str(e)}})
            break

    return steps_out, last_data
