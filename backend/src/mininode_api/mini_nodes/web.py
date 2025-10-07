import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from typing import List, Dict, Set
import urllib.robotparser as robotparser

UA = "MininodeBot/1.0 (+https://mininode.io)"
DEFAULT_TIMEOUT = 20.0

def normalize_url(base: str, href: str) -> str:
    if not href: return ""
    href = href.strip()
    if href.startswith(("javascript:", "mailto:", "#")): return ""
    absu = urljoin(base, href)
    absu, _ = urldefrag(absu)
    return absu

def is_same_domain(u: str, base: str, allow_subdomains: bool) -> bool:
    pu, pb = urlparse(u), urlparse(base)
    if pu.scheme not in ("http", "https"): return False
    if pu.netloc == pb.netloc: return True
    return allow_subdomains and pu.netloc.endswith("." + pb.netloc)

async def fetch_html(url: str, client: httpx.AsyncClient) -> str:
    r = await client.get(url, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text

async def allowed_by_robots(url: str, client: httpx.AsyncClient) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        r = await client.get(robots_url, headers={"User-Agent": UA})
    except Exception:
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(UA, url)

def discover_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.select("a[href]"):
        u = normalize_url(base_url, a.get("href"))
        if u: links.append(u)
    return links

async def fetch_single_text(url: str, max_chars: int) -> str:
    from .extract import extract_text
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        try:
            html = await fetch_html(url, client)
            return extract_text(html, max_chars=max_chars)
        except Exception:
            return ""

async def crawl_site(
    base_url: str,
    max_pages: int = 5,
    same_domain: bool = True,
    follow_subdomains: bool = False,
    max_chars: int = 12000
) -> List[Dict[str, str]]:
    from .extract import extract_text
    visited: Set[str] = set()
    queue: List[str] = [base_url]
    results: List[Dict[str, str]] = []
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        while queue and len(results) < max_pages:
            url = queue.pop(0)
            if url in visited: continue
            visited.add(url)
            if same_domain and not is_same_domain(url, base_url, allow_subdomains=follow_subdomains):
                continue
            try:
                if not await allowed_by_robots(url, client): 
                    continue
            except Exception:
                pass
            try:
                html = await fetch_html(url, client)
                text = extract_text(html, max_chars=max_chars)
                if text:
                    results.append({"url": url, "text": text})
                for nxt in discover_links(url, html):
                    if nxt not in visited and nxt not in queue:
                        queue.append(nxt)
            except Exception:
                continue
    return results
