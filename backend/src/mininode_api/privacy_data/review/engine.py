"""First, deliberately limited automatic review of a Privacy Data map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from mininode_api.privacy_data.services.data_maps import StoredActivity, StoredDataMap


@dataclass(frozen=True)
class MapObservation:
    code: Literal["D01", "D02", "D03", "D04", "D05", "D06"]
    type: Literal["review", "notice"]
    title: str
    description: str
    activity_id: UUID
    activity_type: str
    third_party_type: str | None = None


def _observation(activity: StoredActivity, **values) -> MapObservation:
    return MapObservation(
        activity_id=activity.id,
        activity_type=activity.activity_type,
        **values,
    )


def review_data_map(
    data_map: StoredDataMap, activities: list[StoredActivity]
) -> list[MapObservation]:
    """Return objective D01-D06 observations without persisting a result."""
    del data_map  # Part of the stable engine boundary; the first rules are activity-only.
    observations: list[MapObservation] = []
    for activity in activities:
        answers = activity.answers
        retention_status = (answers.get("retention") or {}).get("status")
        if retention_status == "unknown":
            observations.append(_observation(
                activity,
                code="D01",
                type="review",
                title="No está claro cuánto tiempo guardas esta información",
                description="Indicaste que no estás seguro del período de conservación. Conviene definir cuánto tiempo necesitas mantener esta información.",
            ))
        if retention_status == "variable":
            observations.append(_observation(
                activity,
                code="D02",
                type="review",
                title="El tiempo de conservación depende del caso",
                description="El período de conservación cambia según la situación. Conviene definir criterios simples para saber cuándo mantener o eliminar esta información.",
            ))
        if "unknown" in (answers.get("access_roles") or []):
            observations.append(_observation(
                activity,
                code="D03",
                type="review",
                title="No está claro quién puede acceder a esta información",
                description="Indicaste que no estás seguro de quién puede acceder. Conviene identificar qué personas o áreas realmente necesitan acceso.",
            ))
        if answers.get("has_third_parties") is True:
            observations.append(_observation(
                activity,
                code="D05",
                type="notice",
                title="Participan personas o empresas externas",
                description="Esta actividad involucra terceros. Conviene tener presente qué información reciben, a qué pueden acceder y para qué la utilizan.",
            ))
            for third_party in answers.get("third_parties") or []:
                if "unknown" in (third_party.get("relationships") or []):
                    observations.append(_observation(
                        activity,
                        code="D04",
                        type="review",
                        title="No está claro qué hace un tercero con la información",
                        description="Hay una persona o empresa externa involucrada, pero no está claro qué ocurre con la información que recibe o puede acceder.",
                        third_party_type=third_party.get("type"),
                    ))
        if answers.get("may_include_minors") is True:
            observations.append(_observation(
                activity,
                code="D06",
                type="review",
                title="Esta actividad podría incluir información de menores de edad",
                description="La información de menores requiere especial atención. Conviene identificar claramente qué datos se manejan y para qué se utilizan.",
            ))
    return observations
