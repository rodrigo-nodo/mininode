"""First, deliberately limited automatic review of a Privacy Data map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from mininode_api.privacy_data.services.data_maps import StoredActivity, StoredDataMap


@dataclass(frozen=True)
class MapObservation:
    code: Literal["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10", "D11", "D12", "D13"]
    type: Literal["review", "notice"]
    topic: str
    action: str
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
    """Return objective D01-D13 observations without persisting a result."""
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
                topic="Conservación",
                action="Define cuánto tiempo necesitas conservar estos datos.",
                title="No está claro cuánto tiempo guardas esta información",
                description="Indicaste que no estás seguro del período de conservación. Conviene definir cuánto tiempo necesitas mantener esta información.",
            ))
        if retention_status == "variable":
            observations.append(_observation(
                activity,
                code="D02",
                type="review",
                topic="Conservación",
                action="Define criterios para decidir cuánto tiempo conservarlos según cada caso.",
                title="El tiempo de conservación depende del caso",
                description="El período de conservación cambia según la situación. Conviene definir criterios simples para saber cuándo mantener o eliminar esta información.",
            ))
        if "unknown" in (answers.get("access_roles") or []):
            observations.append(_observation(
                activity,
                code="D03",
                type="review",
                topic="Accesos",
                action="Identifica quién necesita acceder a ellos.",
                title="No está claro quién puede acceder a esta información",
                description="Indicaste que no estás seguro de quién puede acceder. Conviene identificar qué personas o áreas realmente necesitan acceso.",
            ))
        security_measures = answers.get("security_measures") or []
        if "unknown" in security_measures:
            observations.append(_observation(
                activity,
                code="D09",
                type="review",
                topic="Seguridad",
                action="Aclara qué medidas protegen esta información.",
                title="No está claro cómo proteges esta información",
                description="Indicaste que no estás seguro de las medidas de seguridad actuales. Conviene identificar qué protecciones existen hoy.",
            ))
        elif "none" in security_measures:
            observations.append(_observation(
                activity,
                code="D10",
                type="review",
                topic="Seguridad",
                action="Define medidas básicas para proteger esta información.",
                title="No hay medidas de seguridad definidas",
                description="Indicaste que no tienes medidas definidas para esta información. Conviene establecer protecciones básicas acordes a cómo la manejas.",
            ))
        rights_handling = answers.get("rights_handling")
        if rights_handling == "case_by_case":
            observations.append(_observation(
                activity,
                code="D11",
                type="review",
                topic="Derechos",
                action="Define una forma simple y repetible para responder estas solicitudes.",
                title="Las solicitudes se resuelven caso a caso",
                description="Indicaste que las solicitudes sobre datos personales se resuelven caso a caso. Conviene definir pasos simples para responder de forma consistente.",
            ))
        elif rights_handling == "none":
            observations.append(_observation(
                activity,
                code="D12",
                type="review",
                topic="Derechos",
                action="Define cómo recibir y responder solicitudes sobre datos personales.",
                title="No hay una forma definida para responder solicitudes",
                description="Indicaste que no existe una forma definida para atender solicitudes de acceso, corrección o eliminación de datos. Conviene establecer un proceso básico.",
            ))
        elif rights_handling == "unknown":
            observations.append(_observation(
                activity,
                code="D13",
                type="review",
                topic="Derechos",
                action="Aclara quién respondería y qué pasos seguiría ante una solicitud.",
                title="No está claro cómo responderías una solicitud",
                description="Indicaste que no estás seguro de cómo responder una solicitud relacionada con datos personales. Conviene aclarar quién la recibiría y cómo se gestionaría.",
            ))
        if answers.get("has_third_parties") is True:
            observations.append(_observation(
                activity,
                code="D05",
                type="notice",
                topic="Terceros",
                action="Mantén identificados los terceros que participan.",
                title="Participan personas o empresas externas",
                description="Esta actividad involucra terceros. Conviene tener presente qué información reciben, a qué pueden acceder y para qué la utilizan.",
            ))
            for third_party in answers.get("third_parties") or []:
                if "unknown" in (third_party.get("relationships") or []):
                    observations.append(_observation(
                        activity,
                        code="D04",
                        type="review",
                        topic="Terceros",
                        action="Aclara qué información recibe o puede consultar este tercero.",
                        title="No está claro qué hace un tercero con la información",
                        description="Hay una persona o empresa externa involucrada, pero no está claro qué ocurre con la información que recibe o puede acceder.",
                        third_party_type=third_party.get("type"),
                    ))
        elif answers.get("has_third_parties") == "unknown":
            observations.append(_observation(
                activity,
                code="D08",
                type="review",
                topic="Terceros",
                action="Revisa si alguien fuera de tu negocio recibe, puede ver o utiliza esta información.",
                title="No está claro si personas o empresas externas participan",
                description="Aún no está claro si alguien externo participa en esta actividad o tiene contacto con la información.",
            ))
        if answers.get("may_include_minors") is True:
            observations.append(_observation(
                activity,
                code="D06",
                type="review",
                topic="Menores",
                action="Revisa qué datos de menores manejas y para qué.",
                title="Esta actividad podría incluir información de menores de edad",
                description="La información de menores requiere especial atención. Conviene identificar claramente qué datos se manejan y para qué se utilizan.",
            ))
        elif answers.get("may_include_minors") == "unknown":
            observations.append(_observation(
                activity,
                code="D07",
                type="review",
                topic="Menores",
                action="Revisa si entre estas personas podría haber menores de edad.",
                title="No está claro si esta actividad incluye información de menores",
                description="Aún no está claro si la información de esta actividad podría corresponder a menores de edad.",
            ))
    return observations
