# -*- coding: utf-8 -*-
# backend/src/mininode_api/services/analyze_service.py
from __future__ import annotations
import os
from typing import List
from openai import AsyncOpenAI

from mininode_api.core.http_fetcher import fetch_html
from mininode_api.core.extract import extract_payload
from mininode_api.models.analyze import SummaryIn, SummaryOut, SiteSummary

async def analyze_summary_service(body: SummaryIn) -> SummaryOut:
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    client = AsyncOpenAI(api_key=openai_key)

    summaries: List[SiteSummary] = []

    for url in body.urls:
        result = await fetch_html(str(url))
        if not result["ok"]:
            summaries.append(SiteSummary(url=url, text=f"[Error] No se pudo extraer contenido ({result['reason']})."))
            continue

        payload = extract_payload(result["html"])
        content_snippet = (
            f"Título: {payload['title']}\n"
            f"Descripción: {payload['description']}\n"
            f"Texto:\n{payload['text']}\n"
        )

        prompt = (
            f"Idioma: {body.lang or 'es'}.\n"
            f"Instrucción: {body.prompt}\n\n"
            f"--- CONTEXTO DE LA PÁGINA ({url}) ---\n{content_snippet}\n"
            f"--- FIN CONTEXTO ---\n"
            "Responde solo usando el contexto anterior. Si falta info, indícalo explícitamente."
        )

        comp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (comp.choices[0].message.content or "").strip()
        summaries.append(SiteSummary(url=url, text=text))

    if len(summaries) >= 2:
        cmp_prompt = (
            f"Idioma: {body.lang or 'es'}.\n"
            "Compara brevemente los sitios usando SOLO la info de los resúmenes previos.\n\n"
            + "\n\n".join([f"{s.url} :: {s.text}" for s in summaries])
        )
        cmp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": cmp_prompt}],
            temperature=0.2,
        )
        compare_text = (cmp.choices[0].message.content or "").strip()
    else:
        compare_text = "No hay suficiente información para comparar."

    return SummaryOut(summaries=summaries, compare=compare_text)
