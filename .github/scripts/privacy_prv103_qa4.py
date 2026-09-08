from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from mininode_api.domain_packs.privacy.diagnostic import run_privacy_diagnostic
from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal, _personal_form
from mininode_api.services.privacy_diagnostic import MAX_PAGES_ATTEMPTED, _needed_categories, _next_candidate
from mininode_api.web_inspector import (
    InspectionFetchResult,
    WebFetcher,
    build_evidence,
    classify_page_candidates,
    discover_include_links,
    extract_page,
)
from mininode_api.web_inspector.fetcher import INSPECTION_BUDGET_SECONDS

EXPECTED_PRODUCT_BASE_SHA = "af45be30224a196b153b50c11edfd2dcc9072bd9"
EXPECTED_FRAMEWORK_VERSION = "0.6"
EXPECTED_CONTROLS = 21

CANDIDATES = [
    # Chile - 60
    ("CL001", "chile", "Retail", "es", "https://www.falabella.com/falabella-cl"),
    ("CL002", "chile", "Retail", "es", "https://www.paris.cl/"),
    ("CL003", "chile", "Retail", "es", "https://simple.ripley.cl/"),
    ("CL004", "chile", "Retail", "es", "https://www.lider.cl/"),
    ("CL005", "chile", "Retail", "es", "https://www.jumbo.cl/"),
    ("CL006", "chile", "Retail", "es", "https://www.sodimac.cl/"),
    ("CL007", "chile", "Retail", "es", "https://www.easy.cl/"),
    ("CL008", "chile", "Retail", "es", "https://www.lapolar.cl/"),
    ("CL009", "chile", "Retail", "es", "https://www.abc.cl/"),
    ("CL010", "chile", "Retail", "es", "https://www.pcfactory.cl/"),
    ("CL011", "chile", "Retail", "es", "https://www.spdigital.cl/"),
    ("CL012", "chile", "Marketplace", "es", "https://www.mercadolibre.cl/"),
    ("CL013", "chile", "Salud", "es", "https://www.clinicaalemana.cl/"),
    ("CL014", "chile", "Salud", "es", "https://www.redsalud.cl/"),
    ("CL015", "chile", "Salud", "es", "https://www.integramedica.cl/"),
    ("CL016", "chile", "Salud", "es", "https://www.indisa.cl/"),
    ("CL017", "chile", "Salud", "es", "https://www.davila.cl/"),
    ("CL018", "chile", "Salud", "es", "https://www.vidaintegra.cl/"),
    ("CL019", "chile", "Salud", "es", "https://www.clinicasantamaria.cl/"),
    ("CL020", "chile", "Salud", "es", "https://www.meds.cl/"),
    ("CL021", "chile", "Salud laboral", "es", "https://www.mutual.cl/"),
    ("CL022", "chile", "Salud laboral", "es", "https://www.achs.cl/"),
    ("CL023", "chile", "Educación", "es", "https://www.duoc.cl/"),
    ("CL024", "chile", "Educación", "es", "https://www.inacap.cl/"),
    ("CL025", "chile", "Educación", "es", "https://www.uchile.cl/"),
    ("CL026", "chile", "Educación", "es", "https://www.uc.cl/"),
    ("CL027", "chile", "Educación", "es", "https://www.unab.cl/"),
    ("CL028", "chile", "Educación", "es", "https://www.udd.cl/"),
    ("CL029", "chile", "Educación", "es", "https://www.uai.cl/"),
    ("CL030", "chile", "Educación", "es", "https://www.uss.cl/"),
    ("CL031", "chile", "Educación", "es", "https://www.uautonoma.cl/"),
    ("CL032", "chile", "Educación", "es", "https://www.utem.cl/"),
    ("CL033", "chile", "Educación", "es", "https://www.usach.cl/"),
    ("CL034", "chile", "Educación", "es", "https://www.umce.cl/"),
    ("CL035", "chile", "Educación", "es", "https://finis.cl/"),
    ("CL036", "chile", "Finanzas", "es", "https://www.bancoestado.cl/"),
    ("CL037", "chile", "Finanzas", "es", "https://www.santander.cl/"),
    ("CL038", "chile", "Finanzas", "es", "https://www.bci.cl/"),
    ("CL039", "chile", "Finanzas", "es", "https://www.scotiabankchile.cl/"),
    ("CL040", "chile", "Finanzas", "es", "https://www.itau.cl/"),
    ("CL041", "chile", "Finanzas", "es", "https://www.coopeuch.cl/"),
    ("CL042", "chile", "Seguros", "es", "https://www.consorcio.cl/"),
    ("CL043", "chile", "Finanzas", "es", "https://www.security.cl/"),
    ("CL044", "chile", "Finanzas", "es", "https://www.principal.cl/"),
    ("CL045", "chile", "Telecom", "es", "https://www.entel.cl/"),
    ("CL046", "chile", "Telecom", "es", "https://ww2.movistar.cl/"),
    ("CL047", "chile", "Telecom", "es", "https://www.wom.cl/"),
    ("CL048", "chile", "Telecom", "es", "https://www.clarochile.cl/"),
    ("CL049", "chile", "Telecom", "es", "https://vtr.com/"),
    ("CL050", "chile", "Viajes", "es", "https://www.latamairlines.com/cl/es"),
    ("CL051", "chile", "Viajes", "es", "https://www.skyairline.com/"),
    ("CL052", "chile", "Viajes", "es", "https://jetsmart.com/cl/es/"),
    ("CL053", "chile", "Energía", "es", "https://www.copec.cl/"),
    ("CL054", "chile", "Energía", "es", "https://www.abastible.cl/"),
    ("CL055", "chile", "Energía", "es", "https://www.lipigas.cl/"),
    ("CL056", "chile", "Servicios básicos", "es", "https://www.aguasandinas.cl/"),
    ("CL057", "chile", "Servicios básicos", "es", "https://www.enel.cl/"),
    ("CL058", "chile", "Servicios básicos", "es", "https://www.metrogas.cl/"),
    ("CL059", "chile", "Logística", "es", "https://www.chilexpress.cl/"),
    ("CL060", "chile", "Logística", "es", "https://www.starken.cl/"),
    # Latinoamérica - 20
    ("LA001", "latam", "Delivery", "es", "https://www.rappi.com/"),
    ("LA002", "latam", "Viajes", "es", "https://www.despegar.com/"),
    ("LA003", "latam", "Automotriz", "es", "https://www.kavak.com/"),
    ("LA004", "latam", "Fintech", "es", "https://konfio.mx/"),
    ("LA005", "latam", "Fintech", "es", "https://www.clip.mx/"),
    ("LA006", "latam", "Fintech", "es", "https://www.kueski.com/"),
    ("LA007", "latam", "Fintech", "es", "https://www.uala.com.ar/"),
    ("LA008", "latam", "Fintech", "es", "https://www.naranjax.com/"),
    ("LA009", "latam", "E-commerce", "es", "https://www.tiendanube.com/"),
    ("LA010", "latam", "Educación", "es", "https://platzi.com/"),
    ("LA011", "latam", "Educación", "es", "https://www.crehana.com/"),
    ("LA012", "latam", "Tecnología", "es", "https://www.globant.com/"),
    ("LA013", "latam", "Fintech", "en", "https://www.dlocal.com/"),
    ("LA014", "latam", "Salud", "es", "https://www.doctoralia.com.mx/"),
    ("LA015", "latam", "Finanzas", "es", "https://www.bancolombia.com/"),
    ("LA016", "latam", "Finanzas", "es", "https://www.davivienda.com/"),
    ("LA017", "latam", "Fintech", "es", "https://www.mercadopago.com/"),
    ("LA018", "latam", "Delivery", "es", "https://www.pedidosya.com/"),
    ("LA019", "latam", "Viajes", "es", "https://www.aeromexico.com/"),
    ("LA020", "latam", "Viajes", "es", "https://www.avianca.com/"),
    # Internacional - 20
    ("IN001", "intl", "SaaS", "en", "https://www.hubspot.com/"),
    ("IN002", "intl", "SaaS", "en", "https://mailchimp.com/"),
    ("IN003", "intl", "SaaS", "en", "https://asana.com/"),
    ("IN004", "intl", "SaaS", "en", "https://www.atlassian.com/"),
    ("IN005", "intl", "SaaS", "en", "https://www.notion.com/"),
    ("IN006", "intl", "SaaS", "en", "https://www.airtable.com/"),
    ("IN007", "intl", "SaaS", "en", "https://www.dropbox.com/"),
    ("IN008", "intl", "SaaS", "en", "https://www.box.com/"),
    ("IN009", "intl", "SaaS", "en", "https://www.twilio.com/"),
    ("IN010", "intl", "SaaS", "en", "https://www.datadoghq.com/"),
    ("IN011", "intl", "SaaS", "en", "https://www.snowflake.com/"),
    ("IN012", "intl", "SaaS", "en", "https://www.cloudflare.com/"),
    ("IN013", "intl", "SaaS", "en", "https://miro.com/"),
    ("IN014", "intl", "SaaS", "en", "https://www.canva.com/"),
    ("IN015", "intl", "SaaS", "en", "https://www.freshworks.com/"),
    ("IN016", "intl", "SaaS", "en", "https://www.salesforce.com/"),
    ("IN017", "intl", "SaaS", "en", "https://www.typeform.com/"),
    ("IN018", "intl", "SaaS", "en", "https://zapier.com/"),
    ("IN019", "intl", "SaaS", "en", "https://www.semrush.com/"),
    ("IN020", "intl", "SaaS", "en", "https://www.squarespace.com/"),
]


def clean_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.lower().rstrip(".")
    try:
        port = parts.port
    except ValueError:
        port = None
    if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
        host = f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", "", ""))


def compact_text(value, limit: int) -> str | None:
    if value is None:
        return None
    value = " ".join(str(value).split())
    return value[:limit] or None


def control_result(diagnostic: dict, code: str):
    return next((item for item in diagnostic["controls"] if item["control_code"] == code), None)


def normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def dedupe_high(forms: list[dict], region: str) -> list[dict]:
    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[dict] = []
    for form in forms:
        if form["personal_confidence"] != "high":
            continue
        key = (
            form.get("hostname") or "",
            normalized(form.get("heading")),
            normalized(form.get("legend")),
            normalized(form.get("introductory_text")),
            normalized(form.get("submit_text")),
        )
        if key in seen:
            continue
        seen.add(key)
        row = dict(form)
        row["blind_id"] = f"{region.upper()}-{len(result) + 1:03d}"
        result.append(row)
    return result


def reviewer_packet(forms: list[dict], region: str) -> tuple[list[dict], str]:
    blind = []
    lines = [
        f"# PRV-103 QA4 - paquete ciego - {region}",
        "",
        "Clasifica cada caso usando exclusivamente heading, legend, introductory_text y submit_text.",
        "No uses conocimiento externo del sitio.",
        "Clases permitidas: concrete, generic, none, unknown.",
        "",
    ]
    for form in forms:
        item = {
            "blind_id": form["blind_id"],
            "heading": form.get("heading"),
            "legend": form.get("legend"),
            "introductory_text": form.get("introductory_text"),
            "submit_text": form.get("submit_text"),
        }
        blind.append(item)
        lines.extend(
            [
                f"## {item['blind_id']}",
                f"- heading: {item['heading'] or '(vacío)'}",
                f"- legend: {item['legend'] or '(vacío)'}",
                f"- introductory_text: {item['introductory_text'] or '(vacío)'}",
                f"- submit_text: {item['submit_text'] or '(vacío)'}",
                "- clasificación: ",
                "",
            ]
        )
    return blind, "\n".join(lines)


def inspect_case(case_id: str, region: str, sector: str, language: str, requested: str) -> tuple[dict, list[dict]]:
    case = {
        "case_id": case_id,
        "region": region,
        "sector": sector,
        "language": language,
        "requested_url": clean_url(requested),
        "pages_requested": 0,
        "pages_analyzed": 0,
        "errors": [],
        "prv101": None,
        "prv103": None,
    }
    forms: list[dict] = []
    deadline = time.monotonic() + INSPECTION_BUDGET_SECONDS
    attempted_urls = {requested}
    categories_attempted: list[str] = []

    try:
        with WebFetcher(inspection_budget=INSPECTION_BUDGET_SECONDS) as fetcher:
            home_result = fetcher.fetch(requested, [requested], deadline=deadline)
            case["pages_requested"] = 1
            if (
                home_result.pages_fetched != 1
                or not home_result.pages
                or home_result.pages[0].error
                or home_result.pages[0].html is None
                or home_result.pages[0].final_url is None
            ):
                page = home_result.pages[0] if home_result.pages else None
                case["errors"].append(
                    {
                        "phase": getattr(page, "failure_phase", None) or "home_fetch",
                        "code": getattr(getattr(page, "error", None), "code", None) or "inspection_failed",
                        "status_code": getattr(page, "status_code", None),
                    }
                )
                return case, forms

            home_page = home_result.pages[0]
            home_evidence = extract_page(home_page.html, home_page.final_url)
            try:
                include_links = discover_include_links(
                    home_page.html,
                    home_page.final_url,
                    fetcher=fetcher,
                    deadline=deadline,
                )
            except Exception as exc:
                include_links = []
                case["errors"].append({"phase": "include_discovery", "code": type(exc).__name__})

            candidates = classify_page_candidates(home_page.final_url, [*home_evidence.links, *include_links])
            attempted_urls.add(home_page.final_url)
            combined = InspectionFetchResult(
                target_url=requested,
                pages_requested=1,
                pages_fetched=1,
                pages=list(home_result.pages),
                errors=list(home_result.errors),
            )

            def evaluate():
                contract = build_evidence(combined, additional_links=include_links)
                return contract, run_privacy_diagnostic(contract)

            contract, diagnostic = evaluate()
            while True:
                needed = _needed_categories(diagnostic)
                if not needed or combined.pages_requested >= MAX_PAGES_ATTEMPTED or time.monotonic() >= deadline:
                    combined.limited |= combined.pages_requested >= MAX_PAGES_ATTEMPTED or time.monotonic() >= deadline
                    break
                candidate = _next_candidate(candidates, attempted_urls, needed)
                if candidate is None:
                    break
                attempted_urls.add(candidate.url)
                categories_attempted.append(candidate.category)
                result = fetcher.fetch(home_page.final_url, [candidate.url], deadline=deadline)
                combined.pages_requested += 1
                combined.pages.extend(result.pages)
                combined.errors.extend(result.errors)
                combined.pages_fetched += result.pages_fetched
                combined.limited |= result.limited
                contract, diagnostic = evaluate()

            contract, diagnostic = evaluate()
            case["pages_requested"] = combined.pages_requested
            case["pages_analyzed"] = combined.pages_fetched
            case["categories_attempted"] = categories_attempted
            case["site_url"] = clean_url(home_page.final_url)
            case["framework_version"] = diagnostic.get("framework_version")
            case["scoring_version"] = diagnostic.get("scoring_version")
            case["prv101"] = control_result(diagnostic, "PRV-101")
            case["prv103"] = control_result(diagnostic, "PRV-103")

            for index, form in enumerate(contract.forms):
                is_personal, confidence = _personal_form(form)
                if not is_personal:
                    continue
                purpose = _form_purpose_signal(form) if confidence == "high" else "unknown"
                forms.append(
                    {
                        "case_id": case_id,
                        "region": region,
                        "sector": sector,
                        "language": language,
                        "source_url": clean_url(form.source_url),
                        "hostname": (urlsplit(form.source_url).hostname or "").lower() or None,
                        "form_index": index,
                        "personal_confidence": confidence,
                        "heading": compact_text(form.heading, 160),
                        "legend": compact_text(form.legend, 160),
                        "introductory_text": compact_text(form.introductory_text, 300),
                        "submit_text": compact_text(form.submit_text, 120),
                        "product_purpose": purpose,
                    }
                )
    except Exception as exc:
        case["errors"].append({"phase": "unexpected", "code": type(exc).__name__})

    return case, forms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", choices=("chile", "latam", "intl"), required=True)
    args = parser.parse_args()

    controls_path = Path("backend/src/mininode_api/domain_packs/privacy/controls.json")
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    assert controls["version"] == EXPECTED_FRAMEWORK_VERSION
    assert len(controls["controls"]) == EXPECTED_CONTROLS

    selected = [case for case in CANDIDATES if case[1] == args.region]
    output = {
        "baseline": {
            "product_base_sha": EXPECTED_PRODUCT_BASE_SHA,
            "runner_sha": os.getenv("GITHUB_SHA"),
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "scoring_version": "0.1",
            "controls": EXPECTED_CONTROLS,
            "region": args.region,
        },
        "cases": [],
        "forms_raw": [],
        "forms_high_deduped": [],
    }

    for case in selected:
        case_result, forms = inspect_case(*case)
        output["cases"].append(case_result)
        output["forms_raw"].extend(forms)

    deduped = dedupe_high(output["forms_raw"], args.region)
    output["forms_high_deduped"] = deduped
    blind, blind_markdown = reviewer_packet(deduped, args.region)

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    internal_path = artifacts / f"privacy-prv103-qa4-{args.region}-internal.json"
    blind_json_path = artifacts / f"privacy-prv103-qa4-{args.region}-blind.json"
    blind_md_path = artifacts / f"privacy-prv103-qa4-{args.region}-reviewer.md"
    internal_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    blind_json_path.write_text(json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8")
    blind_md_path.write_text(blind_markdown, encoding="utf-8")

    summary = {
        "region": args.region,
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
