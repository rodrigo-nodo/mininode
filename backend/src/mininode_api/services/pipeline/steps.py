from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple, List

from ...core import config
from ...core.measure import now_ms, elapsed_ms
from ...core.ids import new_id


def _bucket_dir(name: str) -> Path:
    d = Path(config.DATA_DIR).joinpath(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_chunks(obj: Any, chunk_size: int = 1024 * 1024) -> Iterable[bytes]:
    """
    Best-effort chunk reader that supports FastAPI UploadFile (.file) or raw bytes.
    """
    # If it's an UploadFile-like object, prefer its underlying .file
    file_obj = getattr(obj, "file", None)
    if file_obj is not None and hasattr(file_obj, "read"):
        try:
            try:
                file_obj.seek(0)
            except Exception:
                pass
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                yield chunk
            return
        except Exception:
            pass

    # If it's plain bytes, yield once
    if isinstance(obj, (bytes, bytearray)):
        yield bytes(obj)
        return

    # Last resort: if it has a synchronous read()
    if hasattr(obj, "read"):
        while True:
            chunk = obj.read(chunk_size)
            if not chunk:
                break
            yield chunk
        return

    raise ValueError("Objeto de archivo no soportado para lectura sincrónica")


def step_upload(ctx: Dict[str, Any], args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Guarda el archivo en `uploads/` y devuelve metadatos mínimos.

    Espera en ctx:
      - file: UploadFile (FastAPI) o bytes
    """
    t0 = now_ms()
    src = ctx.get("file")
    if src is None:
        raise ValueError("ctx['file'] requerido para step_upload")

    file_id = new_id("upl")
    dst = _bucket_dir("uploads").joinpath(file_id)
    size = 0
    with open(dst, "wb") as w:
        for chunk in _read_chunks(src):
            size += len(chunk)
            w.write(chunk)

    filename = getattr(src, "filename", None)
    mime = getattr(src, "content_type", None)

    out = {
        "file_id": file_id,
        "filename": filename or "",
        "mime": mime,
        "size": size,
    }
    return out, elapsed_ms(t0)


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


SUPPORTED_OPS = {"deskew", "binarize", "denoise"}


def _otsu_threshold(hist: List[int]) -> int:
    """Calcula umbral de Otsu a partir de histograma (256 bins) sin numpy."""
    total = sum(hist)
    sum_total = sum(i * h for i, h in enumerate(hist))
    sum_b = 0.0
    w_b = 0.0
    var_max = -1.0
    threshold = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        # Between class variance
        var_between = w_b * w_f * (m_b - m_f) * (m_b - m_f)
        if var_between > var_max:
            var_max = var_between
            threshold = t
    return threshold


def _apply_ops_and_save(src: Path, dst: Path, ops_req: List[str]) -> List[str]:
    """
    Abre imagen, aplica operaciones solicitadas y guarda optimizada.
    Devuelve lista de ops aplicadas realmente.
    """
    from PIL import Image, ImageFilter

    ops_applied: List[str] = []
    with Image.open(src) as img_in:
        img = img_in.convert("RGB") if img_in.mode not in ("RGB", "L") else img_in.copy()

        # deskew vía Tesseract OSD si está disponible
        if "deskew" in ops_req:
            try:
                import pytesseract  # type: ignore
                osd = pytesseract.image_to_osd(img_in)
                # Buscar "Rotate: X"
                angle = 0
                for line in osd.splitlines():
                    if "Rotate" in line:
                        try:
                            angle = int(line.split(":")[1].strip())
                        except Exception:
                            angle = 0
                        break
                if angle and angle % 360 != 0:
                    # Pillow rota en sentido antihorario; OSD da rotación a aplicar para enderezar
                    img = img.rotate(-angle, expand=True)
                    ops_applied.append("deskew")
                else:
                    # Si no hay rotación, no la contamos
                    pass
            except Exception:
                # Si falla OSD, no aplicamos deskew
                pass

        # binarize (Otsu)
        if "binarize" in ops_req:
            gray = img.convert("L")
            hist = gray.histogram()  # 256 bins
            thr = _otsu_threshold(hist)
            bw = gray.point(lambda p, t=thr: 255 if p > t else 0, mode="1").convert("L")
            img = bw
            ops_applied.append("binarize")

        # denoise (mediana)
        if "denoise" in ops_req:
            img = img.filter(ImageFilter.MedianFilter(size=3))
            ops_applied.append("denoise")

        # Guardado optimizado
        # Si imagen tiene transparencia, guardamos PNG; si no, JPEG comprimido
        save_kwargs: Dict[str, Any] = {}
        fmt = "PNG" if img.mode in ("RGBA", "LA") else "JPEG"
        if fmt == "JPEG":
            if img.mode in ("RGBA", "LA"):
                img = img.convert("RGB")
            save_kwargs.update(dict(quality=75, optimize=True, progressive=True))
        else:
            save_kwargs.update(dict(optimize=True))

        img.save(dst, format=fmt, **save_kwargs)

    return ops_applied


def step_optimize(ctx: Dict[str, Any], args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Copia el archivo de `uploads/` a `optimized/` (placeholder de optimización) y devuelve métricas.

    Usa en ctx:
      - file_id: id del archivo subido previamente

    Usa en args:
      - ops: List[str] (opcional)
    """
    t0 = now_ms()

    src_id = ctx.get("file_id")
    if not src_id:
        raise ValueError("ctx['file_id'] requerido para step_optimize")

    ops_req: List[str] = [op for op in list(args.get("ops") or []) if op in SUPPORTED_OPS]

    src = _bucket_dir("uploads").joinpath(src_id)
    if not src.exists():
        raise FileNotFoundError(f"file_id no existe en uploads: {src_id}")

    bytes_before = src.stat().st_size
    sha_before = _sha256(src)

    dst_id = new_id("opt")
    dst = _bucket_dir("optimized").joinpath(dst_id)

    # Procesa y guarda
    ops_applied = _apply_ops_and_save(src, dst, ops_req)

    bytes_after = dst.stat().st_size
    sha_after = _sha256(dst)
    size_delta_pct = round(((bytes_after - bytes_before) / max(1, bytes_before)) * 100.0, 2)
    changed = (sha_before != sha_after)

    out: Dict[str, Any] = {
        "src_file_id": src_id,
        "file_id": dst_id,
        "ops_requested": ops_req,
        "ops_applied": ops_applied,
        "metrics": {
            "changed": changed,
            "bytes_before": bytes_before,
            "bytes_after": bytes_after,
            "size_delta_pct": size_delta_pct,
            "sha256_before": sha_before,
            "sha256_after": sha_after,
        },
    }
    return out, elapsed_ms(t0)
