"""Orchestrate Privacy diagnosis, correction-plan building, and persistence."""

from __future__ import annotations

from collections.abc import Mapping

from mininode_api.domain_packs.privacy.correction_plan import build_correction_plan
from mininode_api.services import privacy_correction_plan
from mininode_api.services.privacy_diagnostic import diagnose_privacy_url


class NoActionableItemsError(Exception):
    """The diagnosis has no catalog-backed correction actions to persist."""


def build_and_store_correction_plan(diagnostic: Mapping):
    """Build and persist a plan from one completed diagnostic snapshot."""
    plan = build_correction_plan(
        diagnostic["controls"], initial_score=diagnostic["score"]
    )
    if plan["item_count"] == 0:
        raise NoActionableItemsError(
            "No se identificaron mejoras accionables para generar un Plan de corrección."
        )
    created = privacy_correction_plan.create_correction_plan(
        site_url=diagnostic["site_url"], plan=plan
    )
    return created, plan


def create_correction_plan_from_url(url: str):
    """Inspect a URL once, then build and persist its complete correction plan."""
    diagnostic = diagnose_privacy_url(url)
    return build_and_store_correction_plan(diagnostic)
