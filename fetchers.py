"""
JH Operator — Source Fetchers
==============================
Each function hits a public API and returns a list of jobs in a common format:

    {
        "title":    "Smart Contract Engineer",
        "company":  "Nansen",
        "location": "Remote",
        "url":      "https://...",
        "source":   "greenhouse/nansen",
        "date":     "2026-03-15",           # when posted, if available
        "snippet":  "first ~300 chars of description text"
    }

WHY THESE SOURCES WORK WITHOUT LOGIN:
- Greenhouse, Ashby, and Lever are "Applicant Tracking Systems" (ATS)
- Companies pay them to host job boards
- They all have public JSON APIs — no scraping, no login needed
- We just call the API and parse the JSON response
"""

import json
import time
import urllib.request
import urllib.error
from html import unescape
import re
from datetime import datetime


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities. Returns plain text."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)        # remove tags
    text = re.sub(r"\s+", " ", text).strip()     # collapse whitespace
    return text[:500]  # keep first 500 chars as snippet


def _fetch_json(url: str, timeout: int = 15) -> dict | list | None:
    """Fetch a URL and parse JSON. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JH-Operator/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        print(f"  ⚠ Failed to fetch {url}: {e}")
        return None


def _fetch_html(url: str, timeout: int = 15) -> str | None:
    """Fetch a URL and return raw HTML text. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JH-Operator/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  ⚠ Failed to fetch {url}: {e}")
        return None


# ─── GREENHOUSE ───────────────────────────────────────────────────────
# API docs: https://developers.greenhouse.io/job-board.html
# Endpoint: GET /v1/boards/{board_token}/jobs
# Returns JSON with a "jobs" array

def fetch_greenhouse(board_token: str, company_name: str) -> list[dict]:
    """
    Fetch all jobs from a Greenhouse board.
    
    board_token: the slug from the URL, e.g. "nansen" from greenhouse.io/nansen
    company_name: display name for the report
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    data = _fetch_json(url)
    if not data or "jobs" not in data:
        return []
    
    jobs = []
    for j in data["jobs"]:
        # Greenhouse gives us: title, location.name, absolute_url, updated_at, content
        location = j.get("location", {}).get("name", "Unknown")
        posted = j.get("updated_at", "")[:10]  # "2026-03-15T..." → "2026-03-15"
        
        jobs.append({
            "title":    j.get("title", "Unknown"),
            "company":  company_name,
            "location": location,
            "url":      j.get("absolute_url", ""),
            "source":   f"greenhouse/{board_token}",
            "date":     posted,
            "snippet":  _clean_html(j.get("content", "")),
        })
    return jobs


# ─── ASHBY ────────────────────────────────────────────────────────────
# Ashby has a posting API at: POST https://jobs.ashbyhq.com/api/non-auth/posting
# But the simpler approach is their job board JSON endpoint

def fetch_ashby(company_slug: str, company_name: str) -> list[dict]:
    """
    Fetch all jobs from an Ashby job board.
    
    company_slug: the slug from the URL, e.g. "nethermind" from jobs.ashbyhq.com/nethermind
    """
    # Ashby's public API endpoint for job boards
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    data = _fetch_json(url)
    if not data or "jobs" not in data:
        return []
    
    jobs = []
    for j in data["jobs"]:
        location = j.get("location", "Unknown")
        if isinstance(location, dict):
            location = location.get("name", "Unknown")
        
        posted = j.get("publishedAt", "")[:10] if j.get("publishedAt") else ""
        
        jobs.append({
            "title":    j.get("title", "Unknown"),
            "company":  company_name,
            "location": location if isinstance(location, str) else "Unknown",
            "url":      f"https://jobs.ashbyhq.com/{company_slug}/{j.get('id', '')}",
            "source":   f"ashby/{company_slug}",
            "date":     posted,
            "snippet":  _clean_html(j.get("descriptionHtml", "") or j.get("description", "")),
        })
    return jobs


# ─── LEVER ────────────────────────────────────────────────────────────
# API: GET https://api.lever.co/v0/postings/{company}?mode=json
# Returns a JSON array of postings

def fetch_lever(company_slug: str, company_name: str) -> list[dict]:
    """
    Fetch all jobs from a Lever board.
    
    company_slug: the slug from the URL, e.g. "moonpay" from jobs.lever.co/moonpay
    """
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    data = _fetch_json(url)
    if not data or not isinstance(data, list):
        return []
    
    jobs = []
    for j in data:
        # Lever uses categories.location for location
        location = "Unknown"
        cats = j.get("categories", {})
        if isinstance(cats, dict):
            location = cats.get("location", "Unknown") or "Unknown"
        
        # createdAt is a Unix timestamp in milliseconds
        created_ms = j.get("createdAt", 0)
        posted = ""
        if created_ms:
            posted = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")
        
        jobs.append({
            "title":    j.get("text", "Unknown"),
            "company":  company_name,
            "location": location,
            "url":      j.get("hostedUrl", ""),
            "source":   f"lever/{company_slug}",
            "date":     posted,
            "snippet":  _clean_html(j.get("descriptionPlain", "") or j.get("description", "")),
        })
    return jobs


# ─── WEB3.CAREER ──────────────────────────────────────────────────────
# web3.career has a public page we can parse
# URL pattern: https://web3.career/{keyword}-jobs

def fetch_web3career(keyword: str, label: str) -> list[dict]:
    """
    Fetch jobs from web3.career for a given keyword.
    
    keyword: search slug like "solidity", "blockchain", "smart-contract"
    label: display label for the source
    
    NOTE: This parses HTML, not a JSON API. It's more fragile than ATS fetchers.
    If web3.career changes their HTML, this breaks. That's normal for web scraping.
    """
    url = f"https://web3.career/{keyword}-jobs"
    html = _fetch_html(url)
    if not html:
        return []
    
    jobs = []
    # web3.career uses table rows with class "job_row" or similar
    # We look for patterns in the HTML structure
    # This is a basic regex parser — not beautiful, but works for MVP
    
    # Find job links: they follow pattern /job/{slug}
    # Each job row typically has: title, company, location, date
    rows = re.findall(
        r'<tr[^>]*class="[^"]*job[^"]*"[^>]*>.*?</tr>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    
    for row in rows[:30]:  # limit to first 30 per keyword
        # Extract title from first link
        title_match = re.search(r'<h2[^>]*>(.*?)</h2>', row, re.DOTALL)
        if not title_match:
            title_match = re.search(r'class="[^"]*job[_-]?title[^"]*"[^>]*>(.*?)</', row, re.DOTALL)
        title = _clean_html(title_match.group(1)) if title_match else ""
        
        # Extract URL
        url_match = re.search(r'href="(/[^"]*)"', row)
        job_url = f"https://web3.career{url_match.group(1)}" if url_match else ""
        
        # Extract company
        comp_match = re.search(r'class="[^"]*company[^"]*"[^>]*>(.*?)</', row, re.DOTALL)
        company = _clean_html(comp_match.group(1)) if comp_match else "Unknown"
        
        # Extract location
        loc_match = re.search(r'class="[^"]*location[^"]*"[^>]*>(.*?)</', row, re.DOTALL)
        location = _clean_html(loc_match.group(1)) if loc_match else "Unknown"
        
        if title and len(title) > 3:
            jobs.append({
                "title":    title,
                "company":  company,
                "location": location,
                "url":      job_url,
                "source":   f"web3career/{keyword}",
                "date":     "",  # web3.career doesn't always show clean dates
                "snippet":  "",
            })
    
    return jobs


# ─── CRYPTOJOBSLIST ───────────────────────────────────────────────────

def fetch_cryptojobslist(category: str, label: str) -> list[dict]:
    """
    Fetch jobs from cryptojobslist.com for a given category.
    Similar HTML parsing approach as web3.career.
    """
    url = f"https://cryptojobslist.com/{category}"
    html = _fetch_html(url)
    if not html:
        return []
    
    jobs = []
    # CryptoJobsList uses structured job cards
    # Look for job links
    links = re.findall(
        r'<a[^>]*href="(https://cryptojobslist\.com/jobs/[^"]+)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL
    )
    
    seen_urls = set()
    for job_url, link_text in links[:30]:
        if job_url in seen_urls:
            continue
        seen_urls.add(job_url)
        
        title = _clean_html(link_text)
        if title and len(title) > 5 and len(title) < 200:
            jobs.append({
                "title":    title,
                "company":  "Unknown",  # would need deeper parsing per-job
                "location": "Unknown",
                "url":      job_url,
                "source":   f"cryptojobslist/{category}",
                "date":     "",
                "snippet":  "",
            })
    
    return jobs


# ─── DISPATCHER ───────────────────────────────────────────────────────

def fetch_source(source: dict) -> list[dict]:
    """
    Given a source config dict, call the right fetcher.
    This is the main entry point used by the pipeline.
    """
    src_type = source["type"]
    src_id = source["id"]
    name = source.get("name", src_id)
    
    print(f"  📡 Fetching: {name} ({src_type}/{src_id})")
    
    if src_type == "greenhouse":
        return fetch_greenhouse(src_id, name)
    elif src_type == "ashby":
        return fetch_ashby(src_id, name)
    elif src_type == "lever":
        return fetch_lever(src_id, name)
    elif src_type == "web3career":
        return fetch_web3career(src_id, name)
    elif src_type == "cryptojobslist":
        return fetch_cryptojobslist(src_id, name)
    else:
        print(f"  ⚠ Unknown source type: {src_type}")
        return []
