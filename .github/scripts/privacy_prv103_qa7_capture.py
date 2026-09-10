from __future__ import annotations

import argparse
import json
from pathlib import Path

from privacy_prv103_qa4 import inspect_case

# Production-shadow sites that generated exactly one PRV-103 LLM call in the
# controlled 2026-09-10 sample. Order is frozen before QA7 recapture.
TARGETS = [
    ("P001", "intl", "SaaS", "en", "https://www.brevo.com/"),
    ("P002", "intl", "SaaS", "en", "https://www.mailerlite.com/"),
    ("P003", "intl", "Fintech", "en", "https://plaid.com/"),
    ("P004", "intl", "Payments", "en", "https://www.checkout.com/"),
    ("P005", "intl", "Fintech", "en", "https://www.brex.com/"),
    ("P006", "intl", "Fintech", "en", "https://mercury.com/"),
    ("P007", "intl", "SaaS", "en", "https://www.jotform.com/"),
    ("P008", "intl", "SaaS", "en", "https://www.gitbook.com/"),
    ("P009", "intl", "SaaS", "en", "https://planetscale.com/"),
    ("P010", "intl", "SaaS", "en", "https://fly.io/"),
    ("P011", "intl", "Security", "en", "https://www.gitguardian.com/"),
    ("P012", "intl", "Security", "en", "https://1password.com/"),
    ("P013", "chile", "Automotriz", "es", "https://www.movicenter.cl/"),
    ("P014", "chile", "Automotriz", "es", "https://www.toyota.cl/"),
    ("P015", "chile", "Automotriz", "es", "https://www.hyundai.cl/"),
    ("P016", "chile", "Automotriz", "es", "https://www.suzuki.cl/"),
    ("P017", "chile", "Seguros", "es", "https://www.chubb.com/cl-es/"),
    ("P018", "chile", "Seguros", "es", "https://www.avla.com/cl/"),
    ("P019", "chile", "Prevision", "es", "https://www.afphabitat.cl/"),
    ("P020", "chile", "Salud", "es", "https://www.cruzblanca.cl/"),
    ("P021", "chile", "Salud", "es", "https://www.nuevamasvida.cl/"),
    ("P022", "chile", "Educacion", "es", "https://www.utalca.cl/"),
    ("P023", "chile", "Retail", "es", "https://www.doite.cl/"),
    ("P024", "chile", "Retail", "es", "https://www.sparta.cl/"),
    ("P025", "chile", "Retail", "es", "https://www.guante.cl/"),
    ("P026", "chile", "Retail", "es", "https://www.toyng.cl/"),
    ("P027", "chile", "Software", "es", "https://www.lemontech.com/"),
    ("P028", "chile", "Software", "es", "https://www.rexmas.com/"),
    ("P029", "latam", "Fintech", "es", "https://www.conekta.com/"),
    ("P030", "latam", "Fintech", "es", "https://www.klar.mx/"),
]

ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")


def _norm(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def unique_high(forms: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict] = []
    for form in forms:
        if form.get("personal_confidence") != "high":
            continue
        key = tuple(_norm(form.get(field)) for field in ALLOWED_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        result.append(form)
    return result


def blind_item(blind_id: str, form: dict) -> dict:
    return {"blind_id": blind_id, **{field: form.get(field) for field in ALLOWED_FIELDS}}


def reviewer_markdown(items: list[dict]) -> str:
    lines = [
        "# PRV-103 QA7 - paquete ciego",
        "",
        "Clasifica cada caso usando exclusivamente heading, legend, introductory_text y submit_text.",
        "No uses conocimiento externo del sitio ni intentes identificarlo.",
        "Clases permitidas: concrete, generic, none, unknown.",
        "Devuelve una clase por blind_id y una justificación breve basada solo en el texto visible.",
        "",
    ]
    for item in items:
        lines.append(f"## {item['blind_id']}")
        for field in ALLOWED_FIELDS:
            lines.append(f"- {field}: {item.get(field) or '(vacío)'}")
        lines.append("")
    return "\n".join(lines)


def capture(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    blind: list[dict] = []

    for case_id, region, sector, language, url in TARGETS:
        row = {"case_id": case_id, "url": url, "status": "pending", "high_count": 0}
        try:
            case_result, forms = inspect_case(case_id, region, sector, language, url)
            highs = unique_high(forms)
            row["status"] = "captured"
            row["high_count"] = len(highs)
            row["inspection"] = case_result
            if len(highs) == 1:
                blind_id = f"QA7-{len(blind) + 1:03d}"
                row["reconstruction_eligible"] = True
                row["blind_id"] = blind_id
                blind.append(blind_item(blind_id, highs[0]))
            else:
                row["reconstruction_eligible"] = False
                row["reason"] = "expected_exactly_one_high"
        except Exception as exc:  # QA harness must continue across public-site failures.
            row["status"] = "error"
            row["reconstruction_eligible"] = False
            row["reason"] = exc.__class__.__name__
        manifest.append(row)

    summary = {
        "qa_cycle": "PRV-103 QA7 production-shadow reconstruction",
        "target_sites": len(TARGETS),
        "eligible_sites": len(blind),
        "ineligible_sites": len(TARGETS) - len(blind),
        "allowed_fields": list(ALLOWED_FIELDS),
        "method": "public passive recapture using current Mininode inspector; exactly one deduplicated HIGH form required per site",
        "limitation": "Production telemetry intentionally did not retain semantic form text, so QA7 is a reconstruction, not proof of byte-identical historical input.",
    }

    (output_dir / "qa7_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "qa7_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "qa7_blind.json").write_text(json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "qa7_reviewer.md").write_text(reviewer_markdown(blind), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/privacy-prv103-qa7")
    args = parser.parse_args()
    summary = capture(Path(args.output_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["eligible_sites"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
