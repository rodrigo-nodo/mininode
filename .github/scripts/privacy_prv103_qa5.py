from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from privacy_prv103_qa4 import dedupe_high, inspect_case, reviewer_packet

FROZEN_PRODUCT_SHA = "85cf402ca54efa8f727a172ab19e12c4ba1f0cb8"
EXPECTED_FRAMEWORK_VERSION = "0.7"
EXPECTED_CONTROLS = 21

# Candidate pool frozen before observing any v0.7 QA5 output.
# Tuple: id, organization, region, sector, language, url.
CANDIDATES = [
    ("CL501", "Cencosud", "chile", "Retail", "es", "https://www.cencosud.com/"),
    ("CL502", "SMU", "chile", "Retail", "es", "https://www.smu.cl/"),
    ("CL503", "Unimarc", "chile", "Retail", "es", "https://www.unimarc.cl/"),
    ("CL504", "Tottus", "chile", "Retail", "es", "https://www.tottus.cl/"),
    ("CL505", "Cruz Verde", "chile", "Farmacia", "es", "https://www.cruzverde.cl/"),
    ("CL506", "Salcobrand", "chile", "Farmacia", "es", "https://salcobrand.cl/"),
    ("CL507", "Farmacias Ahumada", "chile", "Farmacia", "es", "https://www.farmaciasahumada.cl/"),
    ("CL508", "Mallplaza", "chile", "Centros comerciales", "es", "https://www.mallplaza.com/cl"),
    ("CL509", "Parque Arauco", "chile", "Centros comerciales", "es", "https://www.parauco.com/"),
    ("CL510", "Casaideas", "chile", "Retail", "es", "https://www.casaideas.cl/"),
    ("CL511", "Tricot", "chile", "Retail", "es", "https://www.tricot.cl/"),
    ("CL512", "Fashion's Park", "chile", "Retail", "es", "https://www.fashionspark.com/"),
    ("CL513", "Corona", "chile", "Retail", "es", "https://www.corona.cl/"),
    ("CL514", "Kitchen Center", "chile", "Retail", "es", "https://www.kitchencenter.cl/"),
    ("CL515", "Rosen", "chile", "Retail", "es", "https://www.rosen.cl/"),
    ("CL516", "CIC", "chile", "Retail", "es", "https://www.cic.cl/"),
    ("CL517", "WePlay", "chile", "Retail", "es", "https://www.weplay.cl/"),
    ("CL518", "Zmart", "chile", "Retail", "es", "https://www.zmart.cl/"),
    ("CL519", "COCHA", "chile", "Viajes", "es", "https://www.cocha.com/"),
    ("CL520", "Turbus", "chile", "Transporte", "es", "https://www.turbus.cl/"),
    ("CL521", "Pullman Bus", "chile", "Transporte", "es", "https://www.pullmanbus.cl/"),
    ("CL522", "Recorrido", "chile", "Transporte", "es", "https://www.recorrido.cl/"),
    ("CL523", "Kupos", "chile", "Transporte", "es", "https://kupos.cl/"),
    ("CL524", "CorreosChile", "chile", "Logistica", "es", "https://www.correos.cl/"),
    ("CL525", "Blue Express", "chile", "Logistica", "es", "https://www.blue.cl/"),
    ("CL526", "Shipit", "chile", "Logistica", "es", "https://www.shipit.cl/"),
    ("CL527", "CGE", "chile", "Servicios basicos", "es", "https://www.cge.cl/"),
    ("CL528", "Saesa", "chile", "Servicios basicos", "es", "https://www.saesa.cl/"),
    ("CL529", "Frontel", "chile", "Servicios basicos", "es", "https://www.frontel.cl/"),
    ("CL530", "Essbio", "chile", "Servicios basicos", "es", "https://www.essbio.cl/"),
    ("CL531", "Esval", "chile", "Servicios basicos", "es", "https://www.esval.cl/"),
    ("CL532", "Aguas Araucania", "chile", "Servicios basicos", "es", "https://www.aguasaraucania.cl/"),
    ("CL533", "Nuevosur", "chile", "Servicios basicos", "es", "https://www.nuevosur.cl/"),
    ("CL534", "Gasco", "chile", "Energia", "es", "https://www.gasco.cl/"),
    ("CL535", "Transbank", "chile", "Pagos", "es", "https://www.transbank.cl/"),
    ("CL536", "Khipu", "chile", "Pagos", "es", "https://khipu.com/"),
    ("CL537", "Flow", "chile", "Pagos", "es", "https://www.flow.cl/"),
    ("CL538", "Tenpo", "chile", "Fintech", "es", "https://www.tenpo.cl/"),
    ("CL539", "Global66", "chile", "Fintech", "es", "https://www.global66.com/"),
    ("CL540", "Cumplo", "chile", "Fintech", "es", "https://cumplo.cl/"),
    ("CL541", "Xepelin", "chile", "Fintech", "es", "https://xepelin.com/"),
    ("CL542", "AgendaPro", "chile", "Software", "es", "https://agendapro.com/"),
    ("CL543", "Nubox", "chile", "Software", "es", "https://www.nubox.com/"),
    ("CL544", "Rankmi", "chile", "Software", "es", "https://www.rankmi.com/"),
    ("CL545", "Talana", "chile", "Software", "es", "https://www.talana.com/"),
    ("CL546", "Chipax", "chile", "Software", "es", "https://www.chipax.com/"),
    ("CL547", "Rindegastos", "chile", "Software", "es", "https://www.rindegastos.com/"),
    ("CL548", "SimpliRoute", "chile", "Software", "es", "https://simpliroute.com/"),
    ("CL549", "Bsale", "chile", "Software", "es", "https://www.bsale.cl/"),
    ("CL550", "Clinica Las Condes", "chile", "Salud", "es", "https://www.clinicalascondes.cl/"),
    ("CL551", "UC Christus", "chile", "Salud", "es", "https://www.ucchristus.cl/"),
    ("CL552", "Bupa Chile", "chile", "Salud", "es", "https://www.bupa.cl/"),
    ("CL553", "Examedi", "chile", "Salud", "es", "https://examedi.com/"),
    ("CL554", "Universidad de los Andes", "chile", "Educacion", "es", "https://www.uandes.cl/"),
    ("CL555", "Universidad Central", "chile", "Educacion", "es", "https://www.ucentral.cl/"),
    ("CL556", "Universidad Mayor", "chile", "Educacion", "es", "https://www.umayor.cl/"),
    ("CL557", "PUCV", "chile", "Educacion", "es", "https://www.pucv.cl/"),
    ("CL558", "UCN", "chile", "Educacion", "es", "https://www.ucn.cl/"),
    ("CL559", "UFRO", "chile", "Educacion", "es", "https://www.ufro.cl/"),
    ("CL560", "UACh", "chile", "Educacion", "es", "https://www.uach.cl/"),
    ("LA501", "Nubank", "latam", "Fintech", "pt", "https://nubank.com.br/"),
    ("LA502", "VTEX", "latam", "E-commerce", "en", "https://vtex.com/"),
    ("LA503", "RD Station", "latam", "Software", "pt", "https://www.rdstation.com/"),
    ("LA504", "Hotmart", "latam", "Tecnologia", "pt", "https://hotmart.com/"),
    ("LA505", "PagBank", "latam", "Fintech", "pt", "https://pagbank.com.br/"),
    ("LA506", "Stone", "latam", "Fintech", "pt", "https://www.stone.com.br/"),
    ("LA507", "Bradesco", "latam", "Finanzas", "pt", "https://banco.bradesco/"),
    ("LA508", "Banco do Brasil", "latam", "Finanzas", "pt", "https://www.bb.com.br/"),
    ("LA509", "BBVA Mexico", "latam", "Finanzas", "es", "https://www.bbva.mx/"),
    ("LA510", "Banorte", "latam", "Finanzas", "es", "https://www.banorte.com/"),
    ("LA511", "Banamex", "latam", "Finanzas", "es", "https://www.banamex.com/"),
    ("LA512", "Coppel", "latam", "Retail", "es", "https://www.coppel.com/"),
    ("LA513", "Liverpool Mexico", "latam", "Retail", "es", "https://www.liverpool.com.mx/"),
    ("LA514", "El Palacio de Hierro", "latam", "Retail", "es", "https://www.elpalaciodehierro.com/"),
    ("LA515", "TOTVS", "latam", "Software", "pt", "https://www.totvs.com/"),
    ("LA516", "Omie", "latam", "Software", "pt", "https://www.omie.com.br/"),
    ("LA517", "Conta Azul", "latam", "Software", "pt", "https://contaazul.com/"),
    ("LA518", "Pipefy", "latam", "Software", "en", "https://www.pipefy.com/"),
    ("LA519", "Wellhub", "latam", "Tecnologia", "en", "https://wellhub.com/"),
    ("LA520", "Descomplica", "latam", "Educacion", "pt", "https://descomplica.com.br/"),
    ("IN501", "Zendesk", "intl", "SaaS", "en", "https://www.zendesk.com/"),
    ("IN502", "Intercom", "intl", "SaaS", "en", "https://www.intercom.com/"),
    ("IN503", "monday.com", "intl", "SaaS", "en", "https://monday.com/"),
    ("IN504", "ClickUp", "intl", "SaaS", "en", "https://clickup.com/"),
    ("IN505", "GitLab", "intl", "SaaS", "en", "https://about.gitlab.com/"),
    ("IN506", "Okta", "intl", "SaaS", "en", "https://www.okta.com/"),
    ("IN507", "Shopify", "intl", "E-commerce", "en", "https://www.shopify.com/"),
    ("IN508", "Stripe", "intl", "Fintech", "en", "https://stripe.com/"),
    ("IN509", "BigCommerce", "intl", "E-commerce", "en", "https://www.bigcommerce.com/"),
    ("IN510", "Klaviyo", "intl", "SaaS", "en", "https://www.klaviyo.com/"),
    ("IN511", "Braze", "intl", "SaaS", "en", "https://www.braze.com/"),
    ("IN512", "Heap", "intl", "SaaS", "en", "https://www.heap.io/"),
    ("IN513", "Mixpanel", "intl", "SaaS", "en", "https://mixpanel.com/"),
    ("IN514", "Amplitude", "intl", "SaaS", "en", "https://amplitude.com/"),
    ("IN515", "New Relic", "intl", "SaaS", "en", "https://newrelic.com/"),
    ("IN516", "Calendly", "intl", "SaaS", "en", "https://calendly.com/"),
    ("IN517", "Figma", "intl", "SaaS", "en", "https://www.figma.com/"),
    ("IN518", "Loom", "intl", "SaaS", "en", "https://www.loom.com/"),
    ("IN519", "CircleCI", "intl", "SaaS", "en", "https://circleci.com/"),
    ("IN520", "DigitalOcean", "intl", "Cloud", "en", "https://www.digitalocean.com/"),
]

HISTORY_PATHS = [
    "docs/privacy-prv103-real-calibration.md",
    "docs/privacy-prv103-real-calibration-qa2.md",
    "docs/privacy-prv103-real-calibration-qa3.md",
    "docs/privacy-prv103-real-calibration-qa4.md",
    "docs/privacy-form-evidence-real-calibration.md",
    "docs/privacy-prv103-calibration-fix4.md",
    ".github/scripts/privacy_prv103_qa4.py",
    ".github/scripts/privacy_prv103_qa4_extension.py",
]


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _history_text() -> tuple[str, str]:
    raw_parts: list[str] = []
    for value in HISTORY_PATHS:
        path = Path(value)
        if path.is_file():
            raw_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    raw = "\n".join(raw_parts).casefold()
    return raw, _norm(raw)


def _is_historical(name: str, url: str, raw_history: str, normalized_history: str) -> bool:
    host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
    if host and host in raw_history:
        return True
    normalized_name = _norm(name)
    return len(normalized_name) >= 5 and normalized_name in normalized_history


def main() -> None:
    controls_path = Path("backend/src/mininode_api/domain_packs/privacy/controls.json")
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    assert controls["version"] == EXPECTED_FRAMEWORK_VERSION
    assert len(controls["controls"]) == EXPECTED_CONTROLS

    raw_history, normalized_history = _history_text()
    accepted = []
    skipped_history = []
    for case_id, organization, region, sector, language, url in CANDIDATES:
        if _is_historical(organization, url, raw_history, normalized_history):
            skipped_history.append({"case_id": case_id, "organization": organization, "url": url})
        else:
            accepted.append((case_id, organization, region, sector, language, url))

    output = {
        "baseline": {
            "frozen_product_sha": FROZEN_PRODUCT_SHA,
            "runner_sha": os.getenv("GITHUB_SHA"),
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "scoring_version": "0.1",
            "controls": EXPECTED_CONTROLS,
            "candidate_pool": len(CANDIDATES),
            "accepted_after_history_guard": len(accepted),
            "skipped_history_count": len(skipped_history),
        },
        "skipped_history": skipped_history,
        "cases": [],
        "forms_raw": [],
        "forms_high_deduped": [],
    }

    for case_id, organization, region, sector, language, url in accepted:
        case_result, forms = inspect_case(case_id, region, sector, language, url)
        case_result["organization"] = organization
        for form in forms:
            form["organization"] = organization
        output["cases"].append(case_result)
        output["forms_raw"].extend(forms)

    deduped = dedupe_high(output["forms_raw"], "qa5")
    output["forms_high_deduped"] = deduped
    blind, blind_markdown = reviewer_packet(deduped, "qa5")

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    (artifacts / "privacy-prv103-qa5-internal.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifacts / "privacy-prv103-qa5-blind.json").write_text(
        json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifacts / "privacy-prv103-qa5-blind.md").write_text(blind_markdown, encoding="utf-8")

    summary = {
        "candidate_pool": len(CANDIDATES),
        "accepted_after_history_guard": len(accepted),
        "skipped_history": len(skipped_history),
        "sites_with_pages": sum(c.get("pages_analyzed", 0) > 0 for c in output["cases"]),
        "personal_forms_raw": len(output["forms_raw"]),
        "high_forms_raw": sum(f.get("personal_confidence") == "high" for f in output["forms_raw"]),
        "medium_forms_raw": sum(f.get("personal_confidence") == "medium" for f in output["forms_raw"]),
        "high_forms_deduped": len(deduped),
    }
    (artifacts / "privacy-prv103-qa5-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("PRV103_QA5_SUMMARY_START")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PRV103_QA5_SUMMARY_END")


if __name__ == "__main__":
    main()
