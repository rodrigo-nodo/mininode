#!/usr/bin/env python3
"""Passive public freshness precheck for a proposed PRV-103 holdout.

This utility only issues GET requests, follows ordinary redirects, and records
transport metadata. It never parses response bodies or runs product code.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "Mininode-PRV103-holdout-precheck/1.0"
ISSUE_223_EXCLUSIONS = frozenset(
    """
helpcrunch.com
helpscout.com
gorgias.com
kustomer.com
gladly.com
dixa.com
crisp.chat
livechat.com
tawk.to
olark.com
zenefits.com
justworks.com
paycor.com
factorialhr.com
hibob.com
recruitee.com
breezy.hr
workable.com
ashbyhq.com
teamtailor.com
freedcamp.com
ntaskmanager.com
basecamp.com
smartsheet.com
teamwork.com
wrike.com
shortcut.com
slab.com
todoist.com
evernote.com
rollbar.com
bugsnag.com
raygun.com
logrocket.com
buddy.works
travis-ci.com
semaphoreci.com
codefresh.io
harness.io
buildkite.com
chargebee.com
mollie.com
meshpayments.com
bill.com
spendesk.com
payoneer.com
klarna.com
affirm.com
afterpay.com
monzo.com
sendlane.com
moengage.com
loops.so
onesignal.com
getresponse.com
sender.net
unbounce.com
instapage.com
plausible.io
june.so
pirsch.io
pendo.io
smartlook.com
mouseflow.com
crazyegg.com
fusionauth.io
duo.com
signwell.com
nordpass.com
surfshark.com
proofpoint.com
mimecast.com
knowbe4.com
huntress.com
sophos.com
fortinet.com
replicate.com
groq.com
huggingface.co
labelbox.com
typesense.org
fauna.com
materialize.com
databricks.com
alation.com
montecarlodata.com
collibra.com
dataiku.com
directus.io
hygraph.com
buttercms.com
formsort.com
wufoo.com
formassembly.com
alchemer.com
questionpro.com
concord.app
qwilr.com
ironcladapp.com
clio.com
""".split()
)


def normalize_hostname(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return hostname[4:] if hostname.startswith("www.") else hostname


def load_domains(path: Path) -> list[str]:
    domains = [normalize_hostname(line) for line in path.read_text().splitlines() if line.strip()]
    if len(domains) != 99:
        raise ValueError(f"expected exactly 99 domains, got {len(domains)}")
    if "" in domains or len(set(domains)) != len(domains):
        raise ValueError("domains must be non-empty and unique after normalization")
    contaminated = sorted(set(domains) & ISSUE_223_EXCLUSIONS)
    if contaminated:
        raise ValueError(
            "domains overlap Issue #223 exclusions: " + ", ".join(contaminated)
        )
    return domains


def precheck(domain: str, timeout: float) -> dict[str, object]:
    request = urllib.request.Request(f"https://{domain}/", headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)  # Establish that a public response body is readable; do not inspect it.
            return {
                "domain": domain,
                "result": "PASS" if 200 <= response.status < 400 else "FAIL",
                "http_status": response.status,
                "final_url": response.url,
                "error": None,
            }
    except urllib.error.HTTPError as error:
        return {"domain": domain, "result": "FAIL", "http_status": error.code, "final_url": error.url, "error": str(error)}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"domain": domain, "result": "FAIL", "http_status": None, "final_url": None, "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("domains", type=Path, help="text file containing exactly 99 domains")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()

    domains = load_domains(args.domains)
    results = [precheck(domain, args.timeout) for domain in domains]
    document = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "public passive GET; redirects followed; one response byte read; no form inspection",
        "result": "PASS" if all(row["result"] == "PASS" for row in results) else "FAIL",
        "sites": results,
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
