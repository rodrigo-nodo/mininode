"""PDF layout evidence: pdfminer blocks, optional tags and original glyph provenance.

The data are candidates, not assertions of correct reading order.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PdfLayoutRegion:
    page: int
    text: str
    bbox: tuple[float, float, float, float]
    source: str = "pdfminer_lttextbox_candidate"

def page_structure_candidates(page, number: int):
    regions = []
    for item in page.objects.get("textboxhorizontal", []):
        value = str(item.get("text") or "").strip()
        if value:
            regions.append(PdfLayoutRegion(
                number, value, tuple(float(item[k]) for k in ("x0", "top", "x1", "bottom"))
            ))
    if len(regions) > 3000:
        raise ValueError("pdf_too_complex")
    regions.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
    tags = set()
    tag_error = None
    try:
        queue = list(page.structure_tree)
        visited = 0
        while queue:
            item = queue.pop()
            visited += 1
            if visited > 20_000:
                raise ValueError("structure_tree_too_complex")
            if isinstance(item, dict):
                tag = item.get("type")
                if isinstance(tag, str):
                    tags.add(tag)
                queue.extend(item.get("children", []))
    except Exception as exc:
        tag_error = type(exc).__name__
        tags.clear()
    return tuple(regions), tuple(sorted(tags)), tag_error

def extract_lines_with_sources(page, original_chars, table_boxes):
    """Use native pdfplumber line building and retain exact source char positions."""
    def in_table(item):
        x = (float(item["x0"]) + float(item["x1"])) / 2
        y = (float(item["top"]) + float(item["bottom"])) / 2
        return any(a <= x <= c and b <= y <= d for a, b, c, d in table_boxes)
    filtered = page.filter(
        lambda obj: obj.get("object_type") != "char" or not in_table(obj)
    )
    original_ids = {id(ch): i for i, ch in enumerate(original_chars)}
    result = []
    for line in filtered.extract_text_lines(layout=False, strip=True, return_chars=True):
        value = str(line["text"]).strip()
        if value:
            result.append((
                value,
                tuple(float(line[k]) for k in ("x0", "top", "x1", "bottom")),
                tuple(original_ids[id(ch)] for ch in line["chars"] if id(ch) in original_ids),
            ))
    return result

def source_coverage_is_unique(original_chars, text_lines, tables):
    """Validate lossless, single-owner glyph assignment; ignore whitespace only.

    The check proves that digitally available content is not lost or
    duplicated between narrative lines and accepted table cells. It DOES
    NOT prove reading order or semantic interpretation.
    """
    owners = {}
    for line in text_lines:
        for index in line.source_char_indices:
            owners[index] = owners.get(index, 0) + 1
    for table in tables:
        for cell in table.cells:
            for index in cell.source_char_indices:
                owners[index] = owners.get(index, 0) + 1
    expected = {index for index, ch in enumerate(original_chars)
                if str(ch.get("text", "")).strip()}
    return all(owners.get(index) == 1 for index in expected)
