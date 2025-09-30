from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid, datetime

@dataclass
class StoredPaths:
    id: str
    image_path: Optional[str]
    json_path: Optional[str]
    meta_path: Optional[str]

class Storage:
    def __init__(self):
        # TODO: leer credenciales desde core.config y preparar cliente (R2/S3/GCS)
        pass

    def save_document_bundle(
        self,
        image_bytes: bytes,
        json_obj: Dict[str, Any],
        meta: Dict[str, Any]
    ) -> StoredPaths:
        job_id = str(uuid.uuid4())
        today = datetime.datetime.utcnow().strftime("%Y/%m/%d")
        base = f"image2json/{today}/{job_id}"
        return StoredPaths(
            id=job_id,
            image_path=f"{base}/input.jpg",
            json_path=f"{base}/output.json",
            meta_path=f"{base}/meta.json",
        )
