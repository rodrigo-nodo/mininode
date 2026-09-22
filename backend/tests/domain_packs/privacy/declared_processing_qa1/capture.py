from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

CASES = [
("Q01","https://superacionpobreza.cl/transparencia/politica-de-cookies-y-privacidad/","privacy_policy"),
("Q02","https://tripglobal.cl/cookies","cookie_policy"),
("Q03","https://policlinicotabancura.cl/politica-de-cookies","cookie_policy"),
("Q04","https://www.zurich.cl/conocenos/politicas-de-privacidad","privacy_policy"),
("Q05","https://fch.cl/politicas-de-privacidad/","privacy_policy"),
("Q06","https://www.justasa.cl/privacidad","privacy_policy"),
("Q07","https://www.anelisa.cl/politica-de-privacidad","privacy_policy"),
("Q08","https://www.alexbrun.cl/politica-de-cookies","cookie_policy"),
("Q09","https://elizatelier.cl/cookies","cookie_policy"),
("Q10","https://www.ida.cl/politicas-de-privacidad","privacy_policy"),
]
out=Path("backend/tests/domain_packs/privacy/declared_processing_qa1/captures"); out.mkdir(parents=True,exist_ok=True)
manifest=[]
headers={"User-Agent":"Mininode-Privacy-QA/1.0 (+public-passive-GET)"}
for cid,url,dtype in CASES:
    row={"case_id":cid,"requested_url":url,"document_type":dtype}
    try:
        r=requests.get(url,headers=headers,timeout=25,allow_redirects=True)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        for tag in soup(["script","style","noscript","svg"]): tag.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else None
        text="\n".join(x.strip() for x in soup.stripped_strings if x.strip())
        text=re.sub(r"\n{3,}","\n\n",text).strip()
        if not text: raise ValueError("empty extracted text")
        p=out/f"{cid}.txt"; p.write_text(text,encoding="utf-8")
        row.update(status="captured",final_url=r.url,captured_at_utc=datetime.now(timezone.utc).isoformat(),
                   sha256=hashlib.sha256(text.encode()).hexdigest(),page_title=title,
                   text_bytes=len(text.encode()),text_path=str(p))
    except Exception as e:
        row.update(status="capture_failed",error=f"{type(e).__name__}: {e}")
    manifest.append(row)
Path(out.parent/"capture_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for r in manifest: print(r["case_id"],r["status"],r.get("sha256","-"),r.get("text_bytes","-"))
