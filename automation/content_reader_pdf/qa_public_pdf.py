"""Non-invasive public smoke QA for digital PDF pages.

Independent expected facts are taken from a manually verified public PDF:
Clínica Santa María's three-page website privacy policy.
"""
from __future__ import annotations

import json
import os
import unicodedata

from mininode_api.content_reader_pdf import PdfReadError, read_public_pdf_url

URL = os.environ.get(
    "CONTENT_READER_PDF_QA_URL",
    "https://drprod-gphdeze8e5bnfegs.a03.azurefd.net/sites/default/files/2025-06/Politica%20de%20Privacidad%20Sitio%20Web.pdf",
)


def normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).casefold()
    return "".join(c for c in folded if not unicodedata.combining(c))


def main() -> int:
    try:
        document = read_public_pdf_url(URL)
    except PdfReadError as error:
        print(json.dumps({"status": "NEEDS_REVIEW", "reason": error.code}, ensure_ascii=False))
        return 1

    # Smoke checks only; do not mistake for pixel-level or full semantic QA.
    page_texts = [normalized(page_text) for page_text in (
        "\n".join(line.text for line in page.lines) for page in document.pages
    )]
    page_count_ok = document.page_count == 3
    main_title_ok = "politica de privacidad" in page_texts[0]
    last_section_ok = "derechos" in page_texts[-1]
    final_date_ok = "noviembre 2024" in page_texts[-1]
    all_pages_text = all(page.lines and page_text.strip() for page, page_text in zip(document.pages, page_texts))
    success = all((page_count_ok, main_title_ok, last_section_ok, final_date_ok, all_pages_text))
    print(json.dumps({
        "status": "PASS" if success else "NEEDS_REVIEW",
        "final_url": document.final_url,
        "file_sha256": document.file_sha256,
        "page_count": document.page_count,
        "character_count": document.character_count,
        "page_lengths": [sum(len(line.text) for line in page.lines) for page in document.pages],
        "table_counts": [len(page.tables) for page in document.pages],
        "table_shapes": [[(len(t.rows), max(map(len, t.rows), default=0)) for t in page.tables] for page in document.pages],
        "integrity_status": document.integrity_status,
        "page_count_matches_reference": page_count_ok,
        "title_on_page_1": main_title_ok,
        "rights_on_last_page": last_section_ok,
        "final_date_on_last_page": final_date_ok,
        "all_pages_have_selectable_text": bool(all_pages_text),
        "scope": "public_pdf_digital_smoke_not_full_visual_equivalence",
    }, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
