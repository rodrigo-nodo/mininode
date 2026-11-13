"""Restricted subprocess entry point for PDF parsing."""
from __future__ import annotations

import json
import resource
import sys
from dataclasses import asdict

from .reader import (
    MAX_PDF_CPU_SECONDS, MAX_PDF_MEMORY_MB, PdfReadError,
    _parse_pdf_in_worker,
)


def main() -> None:
    # The parser never runs in the API process. Limits are installed *before*
    # parsing untrusted bytes. Linux/RenDer runtime target.
    resource.setrlimit(resource.RLIMIT_AS, (MAX_PDF_MEMORY_MB * 1024 * 1024, MAX_PDF_MEMORY_MB * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_PDF_CPU_SECONDS, MAX_PDF_CPU_SECONDS + 1))
    opts = json.loads(sys.argv[1])
    data = sys.stdin.buffer.read(opts["max_bytes"] + 1)
    try:
        document = _parse_pdf_in_worker(data, **opts)
        payload = {"document": asdict(document)}
    except PdfReadError as exc:
        payload = {"error": exc.code}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
