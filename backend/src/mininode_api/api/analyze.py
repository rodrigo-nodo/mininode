from fastapi import APIRouter, HTTPException, Depends
from mininode_api.core.auth import require_api_key
from mininode_api.models.analyze import AnalyzeReq, AnalyzeResp, SummaryItem
from mininode_api.mini_nodes.web import fetch_single_text, crawl_site
from mininode_api.mini_nodes.llm import summarize_text, compare_summaries

router = APIRouter(prefix="/analisis", tags=["Analyze"])

@router.post("/summary", response_model=AnalyzeResp, dependencies=[Depends(require_api_key)])
async def analyze_summary(req: AnalyzeReq):
    if not req.urls:
        raise HTTPException(status_code=400, detail="urls vacías")

    summaries: list[SummaryItem] = []

    if req.scope.lower() == "page":
        for u in req.urls[:5]:
            txt = await fetch_single_text(str(u), max_chars=req.max_chars)
            if not txt:
                summaries.append(SummaryItem(url=str(u), text="No se pudo extraer contenido legible."))
                continue
            s = await summarize_text(txt, lang=req.lang, extra_instruction=req.prompt)
            summaries.append(SummaryItem(url=str(u), text=s))

    elif req.scope.lower() == "site":
        base_url = str(req.urls[0])
        pages = await crawl_site(
            base_url=base_url,
            max_pages=req.max_pages,
            same_domain=req.same_domain,
            follow_subdomains=req.follow_subdomains,
            max_chars=req.max_chars
        )
        if not pages:
            raise HTTPException(status_code=404, detail="No se encontró contenido navegable")
        for p in pages:
            s = await summarize_text(p["text"], lang=req.lang, extra_instruction=req.prompt)
            summaries.append(SummaryItem(url=p["url"], text=s))
    else:
        raise HTTPException(status_code=400, detail='scope debe ser "page" o "site"')

    compare = await compare_summaries([f"{s.url}: {s.text}" for s in summaries], lang=req.lang) if len(summaries) > 1 else None
    return AnalyzeResp(summaries=summaries, compare=compare)
