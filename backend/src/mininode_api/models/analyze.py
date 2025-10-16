# -*- coding: utf-8 -*-
# mininode_api/core/models/analyze.py
from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, HttpUrl
import os
from openai import AsyncOpenAI

# from mininode_api.core.http_fetcher import fetch_html
from ..core.http_fetcher import fetch_html
from ..mini_nodes.extract import extract_payload

# Modelos (puedes moverlos a schemas/ si quieres)
class SummaryIn(BaseModel):
    urls: List[HttpUrl]
    scope: Literal["page", "site"] = "page"
    lang: str = "es"
    prompt: str

class SiteSummary(BaseModel):
    url: HttpUrl
    text: str

class SummaryOut(BaseModel):
    summaries: List[SiteSummary]
    compare: str

async def analisis_summary_service(body: SummaryIn) -> SummaryOut:
    """
    - Descarga HTML (detecta Cloudflare/WAF).
    - Extrae título/descr./texto.
    - Llama a LLM SOLO con ese contexto (no “navega”).
    """
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
