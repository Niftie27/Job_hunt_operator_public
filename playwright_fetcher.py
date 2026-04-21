"""
JH Operator — Playwright Career Page Fetcher
=============================================
Handles companies whose careers pages are JavaScript-rendered and don't expose
a public ATS API (Greenhouse / Ashby / Lever).

The browser is launched ONCE on first use and closed on process exit via atexit,
so all career_page sources share a single Chromium instance across the pipeline run.

Usage (via fetchers.py dispatcher):
    from playwright_fetcher import fetch_career_page
    jobs = fetch_career_page("https://phantom.com/careers", "Phantom")
"""

import atexit
import re
from urllib.parse import urljoin, urlparse

# ─── Shared browser state ─────────────────────────────────────────────

_playwright = None
_browser    = None


def _get_browser():
    """Return the shared Playwright browser, launching it on first call."""
    global _playwright, _browser
    if _browser is None:
        from playwright.sync_api import sync_playwright
        try:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)
            atexit.register(_shutdown_browser)
        except Exception:
            # Reset so the next call retries cleanly instead of hitting the
            # "sync API inside asyncio loop" error from a broken partial state.
            try:
                if _playwright:
                    _playwright.stop()
            except Exception:
                pass
            _playwright = None
            _browser = None
            raise
    return _browser


def _shutdown_browser():
    global _playwright, _browser
    try:
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _browser = None
    _playwright = None


# ─── URL / text filters ───────────────────────────────────────────────

BLOCKED_DOMAINS = [
    "youtube.com", "youtu.be", "twitter.com", "x.com",
    "linkedin.com", "github.com", "medium.com", "discord.com",
    "discord.gg", "t.me", "telegram.org", "reddit.com",
    "facebook.com", "instagram.com", "tiktok.com",
    "docs.google.com", "drive.google.com", "apple.com",
    "play.google.com", "apps.apple.com",
    "cocuma.cz",  # aggregator that surfaces 404 redirect pages
]

# Path segments that strongly suggest a job-posting URL
_JOB_PATH_RE = re.compile(
    r"/(jobs?|careers?|positions?|roles?|openings?|apply|join|vacancies|"
    r"job-detail|job-listing|posting)/",
    re.IGNORECASE,
)

# Words in link text that suggest this is a job title link
_JOB_TITLE_WORDS = re.compile(
    r"\b(engineer|developer|dev|architect|manager|designer|analyst|lead|"
    r"director|researcher|scientist|counsel|recruiter|product|marketing|"
    r"growth|finance|legal|operations?|ops|head of|vp |vice president|"
    r"intern|co-op|coordinator|specialist|strategist|writer|editor)\b",
    re.IGNORECASE,
)


def _looks_like_job_link(href: str, text: str) -> bool:
    if not href or not text:
        return False
    # Block known non-career external domains
    parsed = urlparse(href) if href.startswith("http") else None
    if parsed and any(d in parsed.netloc.lower() for d in BLOCKED_DOMAINS):
        return False
    text = text.strip()
    if len(text) < 3 or len(text) > 200:
        return False
    # Skip navigation / utility links
    if text.lower() in {"careers", "jobs", "open roles", "view all", "see all",
                        "apply", "apply now", "learn more", "back", "home"}:
        return False
    if _JOB_PATH_RE.search(href):
        return True
    if _JOB_TITLE_WORDS.search(text):
        return True
    return False


def _company_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ─── Main fetcher ─────────────────────────────────────────────────────

def fetch_career_page(url: str, company_name: str, default_location: str = "") -> list[dict]:
    """
    Open a career page with Playwright, extract job listing links.

    url:              Full URL of the careers page (the source id in config).
    company_name:     Display name used in pipeline output.
    default_location: Fallback location when extraction returns "Unknown".
    """
    slug = _company_slug(company_name)
    browser = _get_browser()

    try:
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception:
            # Some pages never reach networkidle; fall back to domcontentloaded
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                page.wait_for_timeout(3_000)
            except Exception as e:
                print(f"  ⚠ Playwright: could not load {url}: {e}")
                context.close()
                return []

        # Collect all <a> elements — Playwright returns ElementHandle list
        anchors = page.query_selector_all("a[href]")

        seen_urls: set[str] = set()
        jobs: list[dict] = []

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        for anchor in anchors:
            try:
                href = anchor.get_attribute("href") or ""
                text = (anchor.inner_text() or "").strip()
            except Exception:
                continue

            # Resolve relative URLs
            if href.startswith("http"):
                abs_url = href
            elif href.startswith("/"):
                abs_url = base + href
            else:
                abs_url = urljoin(url, href)

            # Skip anchors, mailto, javascript
            if not abs_url.startswith("http"):
                continue

            if abs_url in seen_urls:
                continue

            if not _looks_like_job_link(abs_url, text):
                continue

            seen_urls.add(abs_url)

            # Try to extract location from multi-line link text
            # Common patterns: "Title\nLocation", "Title · Location"
            raw_text = text
            location = "Unknown"
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            if len(lines) >= 2:
                title_clean = lines[0]
                for line in lines[1:]:
                    line_lower = line.lower()
                    if any(loc in line_lower for loc in [
                        "remote", "hybrid", "onsite", "on-site", "anywhere",
                        "new york", "san francisco", "london", "berlin", "paris",
                        "singapore", "dubai", "tokyo", "toronto", "vancouver",
                        "amsterdam", "zurich", "austin", "seattle", "chicago",
                        "boston", "miami", "los angeles", "bangalore", "poland",
                        "germany", "france", "uk", "usa", "us", "eu", "apac",
                        "emea", "americas", "europe", "asia", "worldwide", "global",
                    ]):
                        location = line
                        break
            else:
                title_clean = raw_text

            if location == "Unknown" and default_location:
                location = default_location

            jobs.append({
                "title":    title_clean,
                "company":  company_name,
                "location": location,
                "url":      abs_url,
                "source":   f"playwright/{slug}",
                "date":     "",
                "snippet":  "",
                "job_id":   "",
            })

        context.close()
        return jobs

    except Exception as e:
        print(f"  ⚠ Playwright: unexpected error for {url}: {e}")
        return []
