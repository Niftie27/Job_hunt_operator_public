"""
JH Operator — Crawl4AI Fetcher

Replaces playwright_fetcher.py for career pages that only show job titles
without descriptions. Uses Crawl4AI with Groq LLM to extract structured
job data (title, location, description) from a two-level crawl:

  Level 1: career page → list of job URLs
  Level 2: each job URL → full description

Requires GROQ_API_KEY (in shell env or .env file at project root).
"""

import asyncio
import json
import os
import re
from urllib.parse import urljoin

from dotenv import load_dotenv

# Load .env from project root so the script works without manual `export`
load_dotenv()


class _LazyImport:
    """Defer crawl4ai import until first call so module-level import never fails."""
    _loaded = False
    AsyncWebCrawler = None
    BrowserConfig = None
    CrawlerRunConfig = None
    LLMConfig = None
    LLMExtractionStrategy = None
    BaseModel = None
    Field = None

    @classmethod
    def load(cls):
        if cls._loaded:
            return
        from crawl4ai import (
            AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig,
            LLMExtractionStrategy,
        )
        from pydantic import BaseModel, Field
        cls.AsyncWebCrawler = AsyncWebCrawler
        cls.BrowserConfig = BrowserConfig
        cls.CrawlerRunConfig = CrawlerRunConfig
        cls.LLMConfig = LLMConfig
        cls.LLMExtractionStrategy = LLMExtractionStrategy
        cls.BaseModel = BaseModel
        cls.Field = Field
        cls._loaded = True


def _company_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _build_schemas():
    _LazyImport.load()
    BaseModel = _LazyImport.BaseModel
    Field = _LazyImport.Field

    class JobListing(BaseModel):
        title: str = Field(..., description="Job title, e.g. 'Senior Backend Engineer'")
        location: str = Field("", description="Location, e.g. 'Remote' or 'Prague' or 'Unknown'")
        url: str = Field(..., description="Full URL to the job detail page")

    class JobDetail(BaseModel):
        title: str = Field(..., description="Job title")
        description: str = Field(..., description="Full job description text, 500-2000 words")
        location: str = Field("", description="Location")
        compensation: str = Field("", description="Salary range if mentioned, e.g. '$120k-$160k'")

    return JobListing, JobDetail


async def _fetch_career_page_async(url: str, company_name: str, default_location: str = "") -> list[dict]:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print(f"     ⚠ {company_name}: GROQ_API_KEY not set, skipping")
        return []

    _LazyImport.load()
    AsyncWebCrawler = _LazyImport.AsyncWebCrawler
    BrowserConfig = _LazyImport.BrowserConfig
    CrawlerRunConfig = _LazyImport.CrawlerRunConfig
    LLMConfig = _LazyImport.LLMConfig
    LLMExtractionStrategy = _LazyImport.LLMExtractionStrategy

    JobListing, JobDetail = _build_schemas()
    slug = _company_slug(company_name)

    llm_config = LLMConfig(
        provider="groq/llama-3.3-70b-versatile",
        api_token=api_key,
    )
    browser_config = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # ── LEVEL 1: extract job links from the career page ──
        print(f"     📄 {company_name}: Level 1 — loading career page")
        level1_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=JobListing.model_json_schema(),
            extraction_type="schema",
            instruction=(
                "Extract EVERY job listing from this career page. "
                "For each one, provide title, location, and the absolute URL "
                "to the job's detail page. Skip navigation links, footer links, "
                "and non-job content. Return a list of JobListing objects."
            ),
            input_format="markdown",
        )
        level1_config = CrawlerRunConfig(
            extraction_strategy=level1_strategy,
            word_count_threshold=10,
        )

        try:
            result = await crawler.arun(url=url, config=level1_config)
            if not result.success:
                print(f"     ⚠ {company_name}: Level 1 failed")
                return []
            listings = json.loads(result.extracted_content) if result.extracted_content else []
        except Exception as e:
            print(f"     ⚠ {company_name}: Level 1 exception: {e}")
            return []

        if not isinstance(listings, list):
            listings = [listings] if isinstance(listings, dict) else []

        print(f"     ✓ {company_name}: found {len(listings)} job listings")

        # Cap to protect Groq free-tier quota
        MAX_JOBS = 15
        if len(listings) > MAX_JOBS:
            print(f"     ⚠ {company_name}: capping at {MAX_JOBS} (had {len(listings)})")
            listings = listings[:MAX_JOBS]

        # ── LEVEL 2: fetch description for each job ──
        jobs: list[dict] = []
        for i, listing in enumerate(listings):
            job_url = listing.get("url", "")
            if not job_url:
                continue
            if not job_url.startswith("http"):
                job_url = urljoin(url, job_url)

            print(f"     📄 {company_name}: Level 2 [{i+1}/{len(listings)}]")

            level2_strategy = LLMExtractionStrategy(
                llm_config=llm_config,
                schema=JobDetail.model_json_schema(),
                extraction_type="schema",
                instruction=(
                    "Extract the job title, full description text "
                    "(include responsibilities, requirements, tech stack, "
                    "benefits — everything relevant to a candidate), "
                    "location, and compensation/salary range if present. "
                    "Description should be the actual job description content, "
                    "not page navigation."
                ),
                input_format="markdown",
            )
            level2_config = CrawlerRunConfig(
                extraction_strategy=level2_strategy,
                word_count_threshold=50,
            )

            try:
                detail = await crawler.arun(url=job_url, config=level2_config)
                if not detail.success or not detail.extracted_content:
                    continue
                parsed = json.loads(detail.extracted_content)
                if not parsed:
                    continue
                detail_obj = parsed[0] if isinstance(parsed, list) else parsed

                jobs.append({
                    "title": detail_obj.get("title") or listing.get("title", ""),
                    "company": company_name,
                    "location": (
                        detail_obj.get("location")
                        or listing.get("location")
                        or default_location
                        or "Unknown"
                    ),
                    "url": job_url,
                    "source": f"crawl4ai/{slug}",
                    "date": "",
                    "snippet": (detail_obj.get("description") or "")[:5000],
                    "compensation": detail_obj.get("compensation", ""),
                    "job_id": "",
                })
            except Exception as e:
                print(f"     ⚠ {company_name}: Level 2 [{i+1}] failed: {e}")
                continue

    return jobs


def fetch_career_page_crawl4ai(url: str, company_name: str, default_location: str = "") -> list[dict]:
    """Sync wrapper for the async crawl, used by the dispatcher in fetchers.py."""
    try:
        return asyncio.run(_fetch_career_page_async(url, company_name, default_location))
    except Exception as e:
        print(f"     ⚠ {company_name}: crawl4ai fatal: {e}")
        return []
