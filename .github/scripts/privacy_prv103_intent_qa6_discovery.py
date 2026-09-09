from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from privacy_prv103_qa4 import dedupe_high, inspect_case, reviewer_packet

FROZEN_MAIN_SHA = "3db94b7c9775e0c23dfc6f2def1fa6de6e23c26c"
EXPECTED_FRAMEWORK_VERSION = "0.6"
EXPECTED_CONTROLS = 21

# Pool frozen before inspecting QA6 outputs.
# Tuple: id, organization, region, sector, language, URL.
CANDIDATES = [
    # Chile
    ("Q6C001", "Autoplanet", "qa6_chile", "Automotriz", "es", "https://www.autoplanet.cl/"),
    ("Q6C002", "Bruno Fritsch", "qa6_chile", "Automotriz", "es", "https://www.brunofritsch.cl/"),
    ("Q6C003", "Coseche", "qa6_chile", "Automotriz", "es", "https://www.coseche.com/"),
    ("Q6C004", "SKBerge", "qa6_chile", "Automotriz", "es", "https://www.skberge.cl/"),
    ("Q6C005", "Inchcape Chile", "qa6_chile", "Automotriz", "es", "https://www.inchcape.cl/"),
    ("Q6C006", "Gildemeister", "qa6_chile", "Automotriz", "es", "https://www.gildemeister.cl/"),
    ("Q6C007", "Americar", "qa6_chile", "Automotriz", "es", "https://www.americar.cl/"),
    ("Q6C008", "Movicenter", "qa6_chile", "Automotriz", "es", "https://www.movicenter.cl/"),
    ("Q6C009", "Toyota Chile", "qa6_chile", "Automotriz", "es", "https://www.toyota.cl/"),
    ("Q6C010", "Kia Chile", "qa6_chile", "Automotriz", "es", "https://www.kia.cl/"),
    ("Q6C011", "Hyundai Chile", "qa6_chile", "Automotriz", "es", "https://www.hyundai.cl/"),
    ("Q6C012", "Mazda Chile", "qa6_chile", "Automotriz", "es", "https://www.mazda.cl/"),
    ("Q6C013", "Nissan Chile", "qa6_chile", "Automotriz", "es", "https://www.nissan.cl/"),
    ("Q6C014", "Chevrolet Chile", "qa6_chile", "Automotriz", "es", "https://www.chevrolet.cl/"),
    ("Q6C015", "Peugeot Chile", "qa6_chile", "Automotriz", "es", "https://www.peugeot.cl/"),
    ("Q6C016", "Citroen Chile", "qa6_chile", "Automotriz", "es", "https://www.citroen.cl/"),
    ("Q6C017", "Ford Chile", "qa6_chile", "Automotriz", "es", "https://www.ford.cl/"),
    ("Q6C018", "Volkswagen Chile", "qa6_chile", "Automotriz", "es", "https://www.volkswagen.cl/"),
    ("Q6C019", "BMW Chile", "qa6_chile", "Automotriz", "es", "https://www.bmw.cl/"),
    ("Q6C020", "Mercedes-Benz Chile", "qa6_chile", "Automotriz", "es", "https://www.mercedes-benz.cl/"),
    ("Q6C021", "Subaru Chile", "qa6_chile", "Automotriz", "es", "https://www.subaru.cl/"),
    ("Q6C022", "Suzuki Chile", "qa6_chile", "Automotriz", "es", "https://www.suzuki.cl/"),
    ("Q6C023", "HDI Seguros Chile", "qa6_chile", "Seguros", "es", "https://www.hdi.cl/"),
    ("Q6C024", "BICE Vida", "qa6_chile", "Seguros", "es", "https://www.bicevida.cl/"),
    ("Q6C025", "Vida Camara", "qa6_chile", "Seguros", "es", "https://www.vidacamara.cl/"),
    ("Q6C026", "Mutual de Seguros de Chile", "qa6_chile", "Seguros", "es", "https://www.mutualdeseguros.cl/"),
    ("Q6C027", "Cardif Chile", "qa6_chile", "Seguros", "es", "https://www.bnpparibascardif.cl/"),
    ("Q6C028", "Southbridge Chile", "qa6_chile", "Seguros", "es", "https://www.southbridge.cl/"),
    ("Q6C029", "Chubb Chile", "qa6_chile", "Seguros", "es", "https://www.chubb.com/cl-es/"),
    ("Q6C030", "AVLA", "qa6_chile", "Seguros", "es", "https://www.avla.com/cl/"),
    ("Q6C031", "AFP Habitat", "qa6_chile", "Prevision", "es", "https://www.afphabitat.cl/"),
    ("Q6C032", "AFP Provida", "qa6_chile", "Prevision", "es", "https://www.provida.cl/"),
    ("Q6C033", "AFP Capital", "qa6_chile", "Prevision", "es", "https://www.afpcapital.cl/"),
    ("Q6C034", "AFP Cuprum", "qa6_chile", "Prevision", "es", "https://www.cuprum.cl/"),
    ("Q6C035", "AFP Modelo", "qa6_chile", "Prevision", "es", "https://www.afpmodelo.cl/"),
    ("Q6C036", "AFP PlanVital", "qa6_chile", "Prevision", "es", "https://www.planvital.cl/"),
    ("Q6C037", "Caja Los Andes", "qa6_chile", "Beneficios", "es", "https://www.cajalosandes.cl/"),
    ("Q6C038", "Caja 18", "qa6_chile", "Beneficios", "es", "https://www.caja18.cl/"),
    ("Q6C039", "Los Heroes", "qa6_chile", "Beneficios", "es", "https://www.losheroes.cl/"),
    ("Q6C040", "Colmena", "qa6_chile", "Salud", "es", "https://www.colmena.cl/"),
    ("Q6C041", "Consalud", "qa6_chile", "Salud", "es", "https://www.consalud.cl/"),
    ("Q6C042", "CruzBlanca", "qa6_chile", "Salud", "es", "https://www.cruzblanca.cl/"),
    ("Q6C043", "Nueva Masvida", "qa6_chile", "Salud", "es", "https://www.nuevamasvida.cl/"),
    ("Q6C044", "Vida Tres", "qa6_chile", "Salud", "es", "https://www.vidatres.cl/"),
    ("Q6C045", "Banmedica", "qa6_chile", "Salud", "es", "https://www.banmedica.cl/"),
    ("Q6C046", "Universidad Alberto Hurtado", "qa6_chile", "Educacion", "es", "https://www.uahurtado.cl/"),
    ("Q6C047", "UCSC", "qa6_chile", "Educacion", "es", "https://www.ucsc.cl/"),
    ("Q6C048", "Universidad de Talca", "qa6_chile", "Educacion", "es", "https://www.utalca.cl/"),
    ("Q6C049", "Universidad Catolica del Maule", "qa6_chile", "Educacion", "es", "https://www.ucm.cl/"),
    ("Q6C050", "Universidad del Bio-Bio", "qa6_chile", "Educacion", "es", "https://www.ubiobio.cl/"),
    ("Q6C051", "Universidad de Playa Ancha", "qa6_chile", "Educacion", "es", "https://www.upla.cl/"),
    ("Q6C052", "Universidad de Tarapaca", "qa6_chile", "Educacion", "es", "https://www.uta.cl/"),
    ("Q6C053", "Universidad de Atacama", "qa6_chile", "Educacion", "es", "https://www.uda.cl/"),
    ("Q6C054", "Universidad de La Serena", "qa6_chile", "Educacion", "es", "https://www.userena.cl/"),
    ("Q6C055", "UNAP", "qa6_chile", "Educacion", "es", "https://www.unap.cl/"),
    ("Q6C056", "Lippi", "qa6_chile", "Retail", "es", "https://www.lippioutdoor.com/"),
    ("Q6C057", "Doite", "qa6_chile", "Retail", "es", "https://www.doite.cl/"),
    ("Q6C058", "Sparta", "qa6_chile", "Retail", "es", "https://www.sparta.cl/"),
    ("Q6C059", "Belsport", "qa6_chile", "Retail", "es", "https://www.belsport.cl/"),
    ("Q6C060", "Guante", "qa6_chile", "Retail", "es", "https://www.guante.cl/"),
    ("Q6C061", "La Fete", "qa6_chile", "Retail", "es", "https://www.lafetechocolat.com/"),
    ("Q6C062", "Varsovienne", "qa6_chile", "Retail", "es", "https://www.varsovienne.cl/"),
    ("Q6C063", "Casa Royal", "qa6_chile", "Retail", "es", "https://www.casaroyal.cl/"),
    ("Q6C064", "Toyng", "qa6_chile", "Retail", "es", "https://www.toyng.cl/"),
    ("Q6C065", "Webdox", "qa6_chile", "Software", "es", "https://www.webdoxclm.com/"),
    ("Q6C066", "Lemontech", "qa6_chile", "Software", "es", "https://www.lemontech.com/"),
    ("Q6C067", "GeoVictoria", "qa6_chile", "Software", "es", "https://www.geovictoria.com/"),
    ("Q6C068", "Haulmer", "qa6_chile", "Software", "es", "https://www.haulmer.com/"),
    ("Q6C069", "Kame ERP", "qa6_chile", "Software", "es", "https://www.kame.cl/"),
    ("Q6C070", "Rexmas", "qa6_chile", "Software", "es", "https://www.rexmas.com/"),

    # Latinoamerica
    ("Q6L001", "Bitso", "qa6_latam", "Fintech", "es", "https://bitso.com/"),
    ("Q6L002", "Conekta", "qa6_latam", "Fintech", "es", "https://www.conekta.com/"),
    ("Q6L003", "Openpay", "qa6_latam", "Fintech", "es", "https://www.openpay.mx/"),
    ("Q6L004", "Stori", "qa6_latam", "Fintech", "es", "https://www.storicard.com/"),
    ("Q6L005", "Klar", "qa6_latam", "Fintech", "es", "https://www.klar.mx/"),
    ("Q6L006", "Belvo", "qa6_latam", "Fintech", "es", "https://belvo.com/"),
    ("Q6L007", "Kushki", "qa6_latam", "Fintech", "es", "https://www.kushkipagos.com/"),
    ("Q6L008", "Pomelo", "qa6_latam", "Fintech", "es", "https://pomelo.la/"),
    ("Q6L009", "Addi", "qa6_latam", "Fintech", "es", "https://co.addi.com/"),
    ("Q6L010", "Nequi", "qa6_latam", "Fintech", "es", "https://www.nequi.com.co/"),
    ("Q6L011", "Bold", "qa6_latam", "Fintech", "es", "https://bold.co/"),
    ("Q6L012", "Creditas", "qa6_latam", "Fintech", "pt", "https://www.creditas.com/"),
    ("Q6L013", "PicPay", "qa6_latam", "Fintech", "pt", "https://picpay.com/"),
    ("Q6L014", "Banco Inter", "qa6_latam", "Fintech", "pt", "https://inter.co/"),
    ("Q6L015", "C6 Bank", "qa6_latam", "Fintech", "pt", "https://www.c6bank.com.br/"),
    ("Q6L016", "XP", "qa6_latam", "Finanzas", "pt", "https://www.xpi.com.br/"),
    ("Q6L017", "Mercado Bitcoin", "qa6_latam", "Fintech", "pt", "https://www.mercadobitcoin.com.br/"),
    ("Q6L018", "QuintoAndar", "qa6_latam", "Inmobiliario", "pt", "https://www.quintoandar.com.br/"),
    ("Q6L019", "Loft", "qa6_latam", "Inmobiliario", "pt", "https://loft.com.br/"),
    ("Q6L020", "iFood", "qa6_latam", "Delivery", "pt", "https://www.ifood.com.br/"),
    ("Q6L021", "Magazine Luiza", "qa6_latam", "Retail", "pt", "https://www.magazineluiza.com.br/"),
    ("Q6L022", "Casas Bahia", "qa6_latam", "Retail", "pt", "https://www.casasbahia.com.br/"),
    ("Q6L023", "Renner", "qa6_latam", "Retail", "pt", "https://www.lojasrenner.com.br/"),
    ("Q6L024", "Riachuelo", "qa6_latam", "Retail", "pt", "https://www.riachuelo.com.br/"),
    ("Q6L025", "Natura Brasil", "qa6_latam", "Retail", "pt", "https://www.natura.com.br/"),
    ("Q6L026", "O Boticario", "qa6_latam", "Retail", "pt", "https://www.boticario.com.br/"),
    ("Q6L027", "Azul", "qa6_latam", "Viajes", "pt", "https://www.voeazul.com.br/"),
    ("Q6L028", "GOL", "qa6_latam", "Viajes", "pt", "https://www.voegol.com.br/"),
    ("Q6L029", "Copa Airlines", "qa6_latam", "Viajes", "es", "https://www.copaair.com/"),
    ("Q6L030", "Volaris", "qa6_latam", "Viajes", "es", "https://www.volaris.com/"),
    ("Q6L031", "Viva Aerobus", "qa6_latam", "Viajes", "es", "https://www.vivaaerobus.com/"),
    ("Q6L032", "Zenvia", "qa6_latam", "Software", "pt", "https://www.zenvia.com/"),
    ("Q6L033", "Take Blip", "qa6_latam", "Software", "pt", "https://www.blip.ai/"),
    ("Q6L034", "Olist", "qa6_latam", "Software", "pt", "https://olist.com/"),
    ("Q6L035", "Bling", "qa6_latam", "Software", "pt", "https://www.bling.com.br/"),
    ("Q6L036", "Siigo", "qa6_latam", "Software", "es", "https://www.siigo.com/"),
    ("Q6L037", "Alegra", "qa6_latam", "Software", "es", "https://www.alegra.com/"),
    ("Q6L038", "Rocket.Chat", "qa6_latam", "Software", "en", "https://www.rocket.chat/"),
    ("Q6L039", "Alura", "qa6_latam", "Educacion", "pt", "https://www.alura.com.br/"),
    ("Q6L040", "Rocketseat", "qa6_latam", "Educacion", "pt", "https://www.rocketseat.com.br/"),

    # Internacional
    ("Q6I001", "HashiCorp", "qa6_intl", "SaaS", "en", "https://www.hashicorp.com/"),
    ("Q6I002", "Snyk", "qa6_intl", "SaaS", "en", "https://snyk.io/"),
    ("Q6I003", "Cloudinary", "qa6_intl", "SaaS", "en", "https://cloudinary.com/"),
    ("Q6I004", "Sanity", "qa6_intl", "SaaS", "en", "https://www.sanity.io/"),
    ("Q6I005", "Pipedrive", "qa6_intl", "SaaS", "en", "https://www.pipedrive.com/"),
    ("Q6I006", "Zoho", "qa6_intl", "SaaS", "en", "https://www.zoho.com/"),
    ("Q6I007", "Brevo", "qa6_intl", "SaaS", "en", "https://www.brevo.com/"),
    ("Q6I008", "Customer.io", "qa6_intl", "SaaS", "en", "https://customer.io/"),
    ("Q6I009", "Iterable", "qa6_intl", "SaaS", "en", "https://iterable.com/"),
    ("Q6I010", "MailerLite", "qa6_intl", "SaaS", "en", "https://www.mailerlite.com/"),
    ("Q6I011", "Kit", "qa6_intl", "SaaS", "en", "https://kit.com/"),
    ("Q6I012", "Drip", "qa6_intl", "SaaS", "en", "https://www.drip.com/"),
    ("Q6I013", "Deel", "qa6_intl", "SaaS", "en", "https://www.deel.com/"),
    ("Q6I014", "Rippling", "qa6_intl", "SaaS", "en", "https://www.rippling.com/"),
    ("Q6I015", "Gusto", "qa6_intl", "SaaS", "en", "https://gusto.com/"),
    ("Q6I016", "BambooHR", "qa6_intl", "SaaS", "en", "https://www.bamboohr.com/"),
    ("Q6I017", "Remote", "qa6_intl", "SaaS", "en", "https://remote.com/"),
    ("Q6I018", "Personio", "qa6_intl", "SaaS", "en", "https://www.personio.com/"),
    ("Q6I019", "Greenhouse", "qa6_intl", "SaaS", "en", "https://www.greenhouse.com/"),
    ("Q6I020", "Lever", "qa6_intl", "SaaS", "en", "https://www.lever.co/"),
    ("Q6I021", "Plaid", "qa6_intl", "Fintech", "en", "https://plaid.com/"),
    ("Q6I022", "Adyen", "qa6_intl", "Fintech", "en", "https://www.adyen.com/"),
    ("Q6I023", "Checkout.com", "qa6_intl", "Fintech", "en", "https://www.checkout.com/"),
    ("Q6I024", "Wise", "qa6_intl", "Fintech", "en", "https://wise.com/"),
    ("Q6I025", "Revolut", "qa6_intl", "Fintech", "en", "https://www.revolut.com/"),
    ("Q6I026", "Brex", "qa6_intl", "Fintech", "en", "https://www.brex.com/"),
    ("Q6I027", "Ramp", "qa6_intl", "Fintech", "en", "https://ramp.com/"),
    ("Q6I028", "Mercury", "qa6_intl", "Fintech", "en", "https://mercury.com/"),
    ("Q6I029", "PandaDoc", "qa6_intl", "SaaS", "en", "https://www.pandadoc.com/"),
    ("Q6I030", "Framer", "qa6_intl", "SaaS", "en", "https://www.framer.com/"),
    ("Q6I031", "Jotform", "qa6_intl", "SaaS", "en", "https://www.jotform.com/"),
    ("Q6I032", "Formstack", "qa6_intl", "SaaS", "en", "https://www.formstack.com/"),
    ("Q6I033", "SurveyMonkey", "qa6_intl", "SaaS", "en", "https://www.surveymonkey.com/"),
    ("Q6I034", "Paperform", "qa6_intl", "SaaS", "en", "https://paperform.co/"),
    ("Q6I035", "Ghost", "qa6_intl", "SaaS", "en", "https://ghost.org/"),
    ("Q6I036", "GitBook", "qa6_intl", "SaaS", "en", "https://www.gitbook.com/"),
    ("Q6I037", "Coda", "qa6_intl", "SaaS", "en", "https://coda.io/"),
    ("Q6I038", "Retool", "qa6_intl", "SaaS", "en", "https://retool.com/"),
    ("Q6I039", "Supabase", "qa6_intl", "Cloud", "en", "https://supabase.com/"),
    ("Q6I040", "PlanetScale", "qa6_intl", "Cloud", "en", "https://planetscale.com/"),
    ("Q6I041", "Railway", "qa6_intl", "Cloud", "en", "https://railway.com/"),
    ("Q6I042", "Render", "qa6_intl", "Cloud", "en", "https://render.com/"),
    ("Q6I043", "Fly.io", "qa6_intl", "Cloud", "en", "https://fly.io/"),
    ("Q6I044", "Heroku", "qa6_intl", "Cloud", "en", "https://www.heroku.com/"),
    ("Q6I045", "JetBrains", "qa6_intl", "Software", "en", "https://www.jetbrains.com/"),
    ("Q6I046", "Docker", "qa6_intl", "Software", "en", "https://www.docker.com/"),
    ("Q6I047", "GitKraken", "qa6_intl", "Software", "en", "https://www.gitkraken.com/"),
    ("Q6I048", "GitGuardian", "qa6_intl", "Security", "en", "https://www.gitguardian.com/"),
    ("Q6I049", "1Password", "qa6_intl", "Security", "en", "https://1password.com/"),
    ("Q6I050", "Dashlane", "qa6_intl", "Security", "en", "https://www.dashlane.com/"),
    ("Q6I051", "LastPass", "qa6_intl", "Security", "en", "https://www.lastpass.com/"),
    ("Q6I052", "Proton", "qa6_intl", "Security", "en", "https://proton.me/"),
    ("Q6I053", "Fastly", "qa6_intl", "Cloud", "en", "https://www.fastly.com/"),
    ("Q6I054", "Akamai", "qa6_intl", "Cloud", "en", "https://www.akamai.com/"),
]

HISTORY_PATHS = [
    "docs/privacy-form-evidence-real-calibration.md",
    "docs/privacy-prv103-real-calibration.md",
    "docs/privacy-prv103-real-calibration-qa2.md",
    "docs/privacy-prv103-real-calibration-qa3.md",
    "docs/privacy-prv103-real-calibration-qa4.md",
    "docs/privacy-prv103-calibration-fix4.md",
    ".github/scripts/privacy_prv103_qa4.py",
    ".github/scripts/privacy_prv103_qa4_extension.py",
]

# QA5 was executed on a temporary script that is not present on main.
QA5_HOSTS = {
    "cencosud.com", "smu.cl", "unimarc.cl", "tottus.cl", "cruzverde.cl", "salcobrand.cl",
    "farmaciasahumada.cl", "mallplaza.com", "parauco.com", "casaideas.cl", "tricot.cl",
    "fashionspark.com", "corona.cl", "kitchencenter.cl", "rosen.cl", "cic.cl", "weplay.cl",
    "zmart.cl", "cocha.com", "turbus.cl", "pullmanbus.cl", "recorrido.cl", "kupos.cl",
    "correos.cl", "blue.cl", "shipit.cl", "cge.cl", "saesa.cl", "frontel.cl", "essbio.cl",
    "esval.cl", "aguasaraucania.cl", "nuevosur.cl", "gasco.cl", "transbank.cl", "khipu.com",
    "flow.cl", "tenpo.cl", "global66.com", "cumplo.cl", "xepelin.com", "agendapro.com",
    "nubox.com", "rankmi.com", "talana.com", "chipax.com", "rindegastos.com", "simpliroute.com",
    "bsale.cl", "clinicalascondes.cl", "ucchristus.cl", "bupa.cl", "examedi.com", "uandes.cl",
    "ucentral.cl", "umayor.cl", "pucv.cl", "ucn.cl", "ufro.cl", "uach.cl", "nubank.com.br",
    "vtex.com", "rdstation.com", "hotmart.com", "pagbank.com.br", "stone.com.br", "bradesco",
    "bb.com.br", "bbva.mx", "banorte.com", "banamex.com", "coppel.com", "liverpool.com.mx",
    "elpalaciodehierro.com", "totvs.com", "omie.com.br", "contaazul.com", "pipefy.com", "wellhub.com",
    "descomplica.com.br", "zendesk.com", "intercom.com", "monday.com", "clickup.com", "gitlab.com",
    "okta.com", "shopify.com", "stripe.com", "bigcommerce.com", "klaviyo.com", "braze.com", "heap.io",
    "mixpanel.com", "amplitude.com", "newrelic.com", "calendly.com", "figma.com", "loom.com",
    "circleci.com", "digitalocean.com",
}


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _history() -> tuple[str, str]:
    parts: list[str] = []
    for value in HISTORY_PATHS:
        path = Path(value)
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    raw = "\n".join(parts).casefold()
    return raw, _norm(raw)


def _hostname(url: str) -> str:
    return (urlsplit(url).hostname or "").casefold().removeprefix("www.")


def _historical(name: str, url: str, raw: str, normalized: str) -> bool:
    host = _hostname(url)
    if host in QA5_HOSTS:
        return True
    if host and host in raw:
        return True
    normalized_name = _norm(name)
    return len(normalized_name) >= 5 and normalized_name in normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", choices=("qa6_chile", "qa6_latam", "qa6_intl"), required=True)
    args = parser.parse_args()

    controls = json.loads(Path("backend/src/mininode_api/domain_packs/privacy/controls.json").read_text(encoding="utf-8"))
    assert controls["version"] == EXPECTED_FRAMEWORK_VERSION
    assert len(controls["controls"]) == EXPECTED_CONTROLS

    raw_history, normalized_history = _history()
    selected = []
    excluded = []
    for item in CANDIDATES:
        case_id, name, region, sector, language, url = item
        if region != args.region:
            continue
        if _historical(name, url, raw_history, normalized_history):
            excluded.append({"case_id": case_id, "organization": name, "hostname": _hostname(url)})
        else:
            selected.append(item)

    output = {
        "baseline": {
            "frozen_main_sha": FROZEN_MAIN_SHA,
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "controls": EXPECTED_CONTROLS,
            "region": args.region,
        },
        "candidate_count": sum(1 for item in CANDIDATES if item[2] == args.region),
        "historical_exclusions": excluded,
        "cases": [],
        "forms_raw": [],
        "forms_high_deduped": [],
    }

    for case_id, _name, region, sector, language, url in selected:
        case_result, forms = inspect_case(case_id, region, sector, language, url)
        output["cases"].append(case_result)
        output["forms_raw"].extend(forms)

    deduped = dedupe_high(output["forms_raw"], args.region)
    output["forms_high_deduped"] = deduped
    blind, blind_md = reviewer_packet(deduped, args.region)

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    prefix = f"privacy-prv103-intent-qa6-{args.region}"
    (artifacts / f"{prefix}-internal.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (artifacts / f"{prefix}-blind.json").write_text(json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8")
    (artifacts / f"{prefix}-reviewer.md").write_text(blind_md, encoding="utf-8")

    summary = {
        "region": args.region,
        "candidates_frozen": output["candidate_count"],
        "historical_excluded": len(excluded),
        "sites_attempted": len(output["cases"]),
        "sites_with_pages": sum(case.get("pages_analyzed", 0) > 0 for case in output["cases"]),
        "personal_forms_raw": len(output["forms_raw"]),
        "high_forms_raw": sum(form.get("personal_confidence") == "high" for form in output["forms_raw"]),
        "medium_forms_raw": sum(form.get("personal_confidence") == "medium" for form in output["forms_raw"]),
        "high_forms_deduped": len(deduped),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
