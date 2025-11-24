#!/usr/bin/env python3
"""
scrape_aajtak.py

Fetch sitemap (using AsyncWebCrawler), extract URLs robustly, and scrape pages.
"""
import asyncio
import os
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from hashlib import sha1
from typing import List, Set
from crawl4ai import AsyncWebCrawler

# -------- CONFIG --------
SITEMAP_URL = "https://www.aajtak.in/rssfeeds/news-sitemap.xml"
OUTPUT_DIR = "pages"
META_DIR = "pages_meta"
LOG_FILE = "pages_failures.log"
PROGRESS_FILE = "pages_done.json"

CONCURRENCY = 4
MAX_RETRIES = 3
BASE_BACKOFF = 1.0
SITEMAP_PREVIEW_CHARS = 800

# -------- SETUP --------
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

SEM = asyncio.Semaphore(CONCURRENCY)


# -------- Helpers --------
def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def url_to_fname(url: str) -> str:
    h = sha1(url.encode("utf-8")).hexdigest()[:12]
    nice = url.replace("https://", "").replace("http://", "").replace("/", "_")
    nice = (nice[:60] + "...") if len(nice) > 60 else nice
    return f"{nice}_{h}"


def load_progress() -> Set[str]:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_progress(done_set: Set[str]):
    tmp = PROGRESS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(list(done_set), f, indent=2)
    os.replace(tmp, PROGRESS_FILE)


def log_failure(url: str, error: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {url}  |  {error}\n")


async def retry_async(fn, *args, max_retries=MAX_RETRIES, base_backoff=BASE_BACKOFF, **kwargs):
    attempt = 0
    while True:
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                raise
            backoff = base_backoff * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)


# -------- Robust sitemap parsing --------
def debug_preview(sitemap_xml: str, n: int = SITEMAP_PREVIEW_CHARS):
    print(f"(sitemap length = {len(sitemap_xml)} bytes)")
    print("=== SITEMAP PREVIEW ===")
    print(sitemap_xml[:n])
    print("=======================")


def extract_urls_from_sitemap_robust(xml_text: str) -> List[str]:
    """
    Robust sitemap <loc> extraction:
    1) try namespace-aware parse
    2) try parse without namespaces
    3) try generic .//loc-like iteration
    4) fallback regex extracting from CDATA or plain <loc> tags
    """
    urls: List[str] = []

    if not xml_text or len(xml_text) < 20:
        return urls

    debug_preview(xml_text, n=SITEMAP_PREVIEW_CHARS)

    # 1) namespace-aware parse
    try:
        root = ET.fromstring(xml_text)
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        found = root.findall("ns:url", ns)
        if found:
            for url_tag in found:
                loc = url_tag.find("ns:loc", ns)
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
            if urls:
                return urls
    except Exception:
        pass

    # 2) parse without namespaces
    try:
        root = ET.fromstring(xml_text)
        found = root.findall("url")
        if found:
            for url_tag in found:
                loc = url_tag.find("loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
            if urls:
                return urls
    except Exception:
        pass

    # 3) generic iteration: match tags ending with 'loc'
    try:
        root = ET.fromstring(xml_text)
        for el in root.iter():
            if el.tag and el.tag.endswith("loc"):
                if el.text:
                    urls.append(el.text.strip())
        if urls:
            return urls
    except Exception:
        pass

    # 4) fallback regex: handles CDATA and plain <loc> tags
    regex = re.compile(r"<loc>\s*(?:<!\[CDATA\[\s*)?(https?://[^<\]\s]+)(?:\s*\]\]>)?\s*</loc>", re.IGNORECASE)
    found = regex.findall(xml_text)
    seen = set()
    clean = []
    for u in found:
        u = u.strip()
        if u not in seen:
            seen.add(u)
            clean.append(u)
    return clean


# -------- Fetch sitemap via AsyncWebCrawler --------
async def fetch_sitemap_via_crawler(url: str, crawler: AsyncWebCrawler) -> str:
    res = await retry_async(crawler.arun, url=url)
    xml_text = getattr(res, "html", "") or ""
    if not xml_text:
        raise RuntimeError("Empty sitemap response from crawler.")
    return xml_text


# -------- Scrape single page --------
async def scrape_single_page(crawler: AsyncWebCrawler, url: str, done_set: Set[str]):
    if url in done_set:
        return

    async with SEM:
        try:
            result = await retry_async(crawler.arun, url=url)

            # Extract markdown (string or object) or fall back to html/extracted_content
            md = ""
            if getattr(result, "markdown", None):
                md_field = result.markdown
                if isinstance(md_field, str):
                    md = md_field
                else:
                    md = getattr(md_field, "raw_markdown", None) or getattr(md_field, "fit_markdown", None) or ""
            if not md:
                md = getattr(result, "extracted_content", None) or getattr(result, "html", "") or ""

            fname = url_to_fname(url)
            md_path = os.path.join(OUTPUT_DIR, f"{fname}.md")
            meta_path = os.path.join(META_DIR, f"{fname}.json")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md or "")

            metadata = {
                "url": url,
                "title": getattr(result, "title", None) or (getattr(result, "metadata", {}) or {}).get("title"),
                "lang": getattr(result, "language", None),
                "status_code": getattr(result, "status_code", None),
                "timestamp": now_iso(),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(f"✔ Saved: {md_path}")

            done_set.add(url)
            save_progress(done_set)

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            log_failure(url, str(e))


# -------- Orchestrator --------
async def scrape_urls_from_sitemap():
    done = load_progress()

    async with AsyncWebCrawler() as crawler:
        print("Fetching sitemap via AsyncWebCrawler...")
        sitemap_xml = await fetch_sitemap_via_crawler(SITEMAP_URL, crawler)

        urls = extract_urls_from_sitemap_robust(sitemap_xml)
        print(f"Found {len(urls)} URLs in sitemap. (Already done: {len(done)})")

        if not urls:
            print("No URLs found. Exiting.")
            return

        to_process = [u for u in urls if u not in done]
        print(f"Will process {len(to_process)} new pages.")

        tasks = [scrape_single_page(crawler, u, done) for u in to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for u, r in zip(to_process, results):
            if isinstance(r, Exception):
                log_failure(u, f"Task-level exception: {r}")


# -------- Main --------
async def main():
    await scrape_urls_from_sitemap()
    print("\n🎉 DONE — all pages processed (or attempted).")


if __name__ == "__main__":
    asyncio.run(main())
