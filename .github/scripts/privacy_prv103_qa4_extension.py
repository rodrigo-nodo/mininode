from __future__ import annotations

import json
import os
from pathlib import Path

from privacy_prv103_qa4 import (
    EXPECTED_CONTROLS,
    EXPECTED_FRAMEWORK_VERSION,
    EXPECTED_PRODUCT_BASE_SHA,
    dedupe_high,
    inspect_case,
    reviewer_packet,
)

EXTENSION = [
    # Chile - 30
    ("CHX001", "extension", "Inmobiliario", "es", "https://www.paz.cl/"),
    ("CHX002", "extension", "Inmobiliario", "es", "https://www.socovesa.cl/"),
    ("CHX003", "extension", "Inmobiliario", "es", "https://www.enaco.cl/"),
    ("CHX004", "extension", "Inmobiliario", "es", "https://www.fundamenta.cl/"),
    ("CHX005", "extension", "Inmobiliario", "es", "https://www.imagina.cl/"),
    ("CHX006", "extension", "Inmobiliario", "es", "https://www.maestra.cl/"),
    ("CHX007", "extension", "Inmobiliario", "es", "https://www.almagro.cl/"),
    ("CHX008", "extension", "Inmobiliario", "es", "https://www.inmobiliariapocuro.cl/"),
    ("CHX009", "extension", "Inmobiliario", "es", "https://www.euroinmobiliaria.cl/"),
    ("CHX010", "extension", "Inmobiliario", "es", "https://www.siena.cl/"),
    ("CHX011", "extension", "Automotriz", "es", "https://www.dercocenter.cl/"),
    ("CHX012", "extension", "Automotriz", "es", "https://www.kaufmann.cl/"),
    ("CHX013", "extension", "Automotriz", "es", "https://www.salazarisrael.cl/"),
    ("CHX014", "extension", "Automotriz", "es", "https://www.portillo.cl/"),
    ("CHX015", "extension", "Automotriz", "es", "https://www.rosselot.cl/"),
    ("CHX016", "extension", "Automotriz", "es", "https://www.curifor.cl/"),
    ("CHX017", "extension", "Seguros", "es", "https://www.metlife.cl/"),
    ("CHX018", "extension", "Seguros", "es", "https://www.zurich.cl/"),
    ("CHX019", "extension", "Seguros", "es", "https://www.mapfre.cl/"),
    ("CHX020", "extension", "Seguros", "es", "https://www.sura.cl/"),
    ("CHX021", "extension", "Educación", "es", "https://www.aiep.cl/"),
    ("CHX022", "extension", "Educación", "es", "https://www.ust.cl/"),
    ("CHX023", "extension", "Educación", "es", "https://www.ipchile.cl/"),
    ("CHX024", "extension", "Educación", "es", "https://ipp.cl/"),
    ("CHX025", "extension", "Software", "es", "https://www.buk.cl/"),
    ("CHX026", "extension", "Empleo", "es", "https://www.getonbrd.com/"),
    ("CHX027", "extension", "Fintech", "es", "https://fintual.cl/"),
    ("CHX028", "extension", "Tecnología", "es", "https://www.betterfly.com/"),
    ("CHX029", "extension", "Alimentos", "es", "https://notco.com/"),
    ("CHX030", "extension", "Software", "es", "https://www.defontana.com/"),
    # Latinoamérica - 10
    ("LAX001", "extension", "Inmobiliario", "es", "https://www.lahaus.com/"),
    ("LAX002", "extension", "Inmobiliario", "es", "https://homie.mx/"),
    ("LAX003", "extension", "Fintech", "es", "https://www.clara.com/"),
    ("LAX004", "extension", "Fintech", "es", "https://www.minu.mx/"),
    ("LAX005", "extension", "Logística", "es", "https://nowports.com/"),
    ("LAX006", "extension", "Educación", "es", "https://www.openenglish.com/"),
    ("LAX007", "extension", "Educación", "es", "https://www.coderhouse.com/"),
    ("LAX008", "extension", "Marketing", "es", "https://rockcontent.com/"),
    ("LAX009", "extension", "Empleo", "es", "https://torre.ai/"),
    ("LAX010", "extension", "Educación", "es", "https://www.laboratoria.la/"),
    # Internacional - 10
    ("INX001", "extension", "SaaS", "en", "https://webflow.com/"),
    ("INX002", "extension", "SaaS", "en", "https://www.wix.com/"),
    ("INX003", "extension", "SaaS", "en", "https://www.docusign.com/"),
    ("INX004", "extension", "SaaS", "en", "https://www.contentful.com/"),
    ("INX005", "extension", "SaaS", "en", "https://www.algolia.com/"),
    ("INX006", "extension", "SaaS", "en", "https://sentry.io/"),
    ("INX007", "extension", "SaaS", "en", "https://www.postman.com/"),
    ("INX008", "extension", "SaaS", "en", "https://www.mongodb.com/"),
    ("INX009", "extension", "SaaS", "en", "https://www.confluent.io/"),
    ("INX010", "extension", "SaaS", "en", "https://www.elastic.co/"),
]


def main() -> None:
    controls_path = Path("backend/src/mininode_api/domain_packs/privacy/controls.json")
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    assert controls["version"] == EXPECTED_FRAMEWORK_VERSION
    assert len(controls["controls"]) == EXPECTED_CONTROLS

    output = {
        "baseline": {
            "product_base_sha": EXPECTED_PRODUCT_BASE_SHA,
            "runner_sha": os.getenv("GITHUB_SHA"),
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "scoring_version": "0.1",
            "controls": EXPECTED_CONTROLS,
            "region": "extension",
        },
        "cases": [],
        "forms_raw": [],
        "forms_high_deduped": [],
    }

    for case in EXTENSION:
        case_result, forms = inspect_case(*case)
        output["cases"].append(case_result)
        output["forms_raw"].extend(forms)

    deduped = dedupe_high(output["forms_raw"], "extension")
    output["forms_high_deduped"] = deduped
    blind, blind_markdown = reviewer_packet(deduped, "extension")

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    internal_path = artifacts / "privacy-prv103-qa4-extension-internal.json"
    blind_json_path = artifacts / "privacy-prv103-qa4-extension-blind.json"
    blind_md_path = artifacts / "privacy-prv103-qa4-extension-reviewer.md"
    internal_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    blind_json_path.write_text(json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8")
    blind_md_path.write_text(blind_markdown, encoding="utf-8")

    summary = {
        "region": "extension",
        "sites_attempted": len(output["cases"]),
        "sites_with_pages": sum(c["pages_analyzed"] > 0 for c in output["cases"]),
        "personal_forms_raw": len(output["forms_raw"]),
        "high_forms_raw": sum(f["personal_confidence"] == "high" for f in output["forms_raw"]),
        "medium_forms_raw": sum(f["personal_confidence"] == "medium" for f in output["forms_raw"]),
        "high_forms_deduped": len(deduped),
    }
    print("PRV103_QA4_SUMMARY_START")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PRV103_QA4_SUMMARY_END")


if __name__ == "__main__":
    main()
