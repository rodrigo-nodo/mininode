# IDs simples (UUIDv4). Suficiente para MVP.
from uuid import uuid4

def new_id(suffix: str | None = None) -> str:
    base = uuid4().hex
    return f"{base}_{suffix}" if suffix else base
