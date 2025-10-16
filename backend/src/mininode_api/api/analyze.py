from fastapi import APIRouter, HTTPException, Depends
from mininode_api.core.auth import require_api_key
from mininode_api.models.analyze import SummaryIn, SummaryOut, SiteSummary
from mininode_api.mini_nodes.web import fetch_single_text, crawl_site
from mininode_api.core.llm import summarize_text, compare_summaries

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# Defaults para parámetros que no están en SummaryIn
DEFAULT_MAX_CHARS = 12000
DEFAULT_MAX_PAGES = 5
DEFAULT_SAME_DOMAIN = True
DEFAULT_FOLLOW_SUBDOMAINS = False

@router.post("/summary", response_model=SummaryOut, dependencies=[Depends(require_api_key)])
async def analyze_summary(req: SummaryIn) -> SummaryOut:
    if not req.urls:
        raise HTTPException(status_code=400, detail="urls vacías")

    summaries: list[SiteSummary] = []

    scope = (req.scope or "page").lower()
    if scope == "page":
        for u in req.urls[:5]:
            txt = await fetch_single_text(str(u), max_chars=DEFAULT_MAX_CHARS)
            if not txt:
                summaries.append(SiteSummary(url=str(u), text="No se pudo extraer contenido legible."))
                continue
            s = await summarize_text(txt, lang=req.lang, extra_instruction=req.prompt)
            summaries.append(SiteSummary(url=str(u), text=s))

    elif scope == "site":
        base_url = str(req.urls[0])
        pages = await crawl_site(
            base_url=base_url,
            max_pages=DEFAULT_MAX_PAGES,
            same_domain=DEFAULT_SAME_DOMAIN,
            follow_subdomains=DEFAULT_FOLLOW_SUBDOMAINS,
            max_chars=DEFAULT_MAX_CHARS,
        )
        if not pages:
            raise HTTPException(status_code=404, detail="No se encontró contenido navegable")
        for p in pages:
            s = await summarize_text(p["text"], lang=req.lang, extra_instruction=req.prompt)
            summaries.append(SiteSummary(url=p["url"], text=s))
    else:
        raise HTTPException(status_code=400, detail='scope debe ser "page" o "site"')

    if len(summaries) > 1:
        compare = await compare_summaries([f"{s.url}: {s.text}" for s in summaries], lang=req.lang)
    else:
        compare = "No hay suficiente información para comparar."
    return SummaryOut(summaries=summaries, compare=compare)
