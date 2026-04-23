"""
JH Operator — Jina AI Reader Fetcher

For career pages where job descriptions live behind a click-through
but the index page DOES expose detail URLs in server-rendered HTML.

Uses Jina Reader (https://r.jina.ai/) to fetch LLM-ready markdown for
each career page and each individual job URL. No API key required for
basic usage; rate limits are generous at our volume.

Limitation: Jina Reader fetches server-side HTML; it does not execute JS.
Career pages that render their listings via JS after page load
(SatoshiLabs, LangChain, Phantom, DFINITY, Arkham, …) expose zero or
one job links in their markdown and will return 0 jobs. Those need a
different strategy (ATS discovery, headless browser, or LLM extraction).
"""

import re
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse


JINA_READER_BASE = "https://r.jina.ai/"

# URL path patterns that identify a job-detail link
JOB_URL_PATTERNS = [
    r"/jobs?/",
    r"/careers?/",
    r"/positions?/",
    r"/roles?/",
    r"/apply/",
    r"/posting/",
    r"jobs\.lever\.co/",
    r"jobs\.ashbyhq\.com/",
    r"boards\.greenhouse\.io/",
    r"\.breezy\.hr/",
]

# Boilerplate link text we never want to treat as a job title
_SKIP_TITLES = {
    "apply", "apply now", "view", "view job", "learn more",
    "read more", "see more", "see all", "see all jobs",
    "careers", "open roles", "open positions",
}


def _fetch_via_jina(url: str, timeout: int = 30) -> str:
    """Fetch URL content via Jina Reader, return markdown (empty on failure)."""
    jina_url = JINA_READER_BASE + url
    try:
        req = urllib.request.Request(
            jina_url,
            headers={
                "User-Agent": "Mozilla/5.0 JH-Operator/1.0",
                "Accept": "text/markdown, text/plain, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"     ⚠ Jina fetch failed for {url}: {type(e).__name__}")
        return ""


def _extract_job_urls(markdown: str, base_url: str) -> list[tuple[str, str]]:
    """Pull (title, url) pairs from markdown links that look like job detail pages."""
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown)

    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    seen: set[str] = set()
    jobs: list[tuple[str, str]] = []

    for title, url in links:
        # Normalise relative URLs
        if url.startswith("/"):
            url = base + url
        elif not url.startswith("http"):
            url = urljoin(base_url, url)

        # Must look like a job-detail URL
        if not any(re.search(p, url, re.I) for p in JOB_URL_PATTERNS):
            continue

        title = title.strip()
        if len(title) < 5 or len(title) > 200:
            continue
        if title.lower() in _SKIP_TITLES:
            continue
        # Ignore image-only link labels like "Image 12: A cute doggy"
        if title.lower().startswith("image "):
            continue

        if url in seen:
            continue
        seen.add(url)
        jobs.append((title, url))

    return jobs


def _company_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch_career_page_jina(
    url: str,
    company_name: str,
    default_location: str = "",
    max_jobs: int = 15,
) -> list[dict]:
    """
    Two-level scrape via Jina Reader.
      Level 1: career page → job URLs
      Level 2: each job URL → full description
    """
    slug = _company_slug(company_name)
    print(f"     📄 {company_name}: Level 1 via Jina")

    level1_md = _fetch_via_jina(url)
    if not level1_md:
        return []

    job_refs = _extract_job_urls(level1_md, url)
    print(f"     ✓ {company_name}: found {len(job_refs)} job URLs")

    if len(job_refs) > max_jobs:
        print(f"     ⚠ {company_name}: capping at {max_jobs} (had {len(job_refs)})")
        job_refs = job_refs[:max_jobs]

    jobs: list[dict] = []
    for i, (title, job_url) in enumerate(job_refs):
        print(f"     📄 {company_name}: Level 2 [{i+1}/{len(job_refs)}]")

        # Be kind to Jina
        time.sleep(0.5)

        detail_md = _fetch_via_jina(job_url)
        snippet = detail_md[:5000] if detail_md else ""

        jobs.append({
            "title":    title,
            "company":  company_name,
            "location": default_location or "Unknown",
            "url":      job_url,
            "source":   f"jina/{slug}",
            "date":     "",
            "snippet":  snippet,
            "job_id":   "",
        })

    return jobs
