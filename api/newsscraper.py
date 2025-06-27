import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time

class NewsScraper:
    """Scrapes news websites for Arsenal transfer rumors using Playwright."""

    def __init__(self):
        self.news_sources = {
            'sky_sports': {
                'url': 'https://www.skysports.com/arsenal-news',
                'parser': self._parse_sky_sports
            },
            # Add other news sources here
        }

    async def _fetch_page_content(self, url):
        """Fetches page content using Playwright to handle dynamic sites."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                # Optional: Add logic to handle cookie banners if they block content
                await page.wait_for_timeout(3000)  # Wait for any lazy-loaded content
                content = await page.content()
                return content
            finally:
                await browser.close()

    async def _parse_sky_sports(self, html, config):
        """Parses the HTML content from Sky Sports."""
        soup = BeautifulSoup(html, 'html.parser')
        rumors = []
        for a in soup.select("a.sdc-site-tile__headline-link"):
            headline = a.get_text(strip=True)
            url = a["href"]
            if not url.startswith("http"):
                url = f"https://www.skysports.com{url}"
            
            rumors.append({
                "headline": headline,
                "source_name": "Sky Sports",
                "url": url,
                "content": "" # We'll let the LLM generate content from the article
            })
        print(f"Found {len(rumors)} potential rumors from Sky Sports.")
        return rumors

    async def scrape_source(self, source_name):
        """Scrapes a single news source."""
        config = self.news_sources[source_name]
        print(f"Scraping {source_name} from {config['url']}...")
        html = await self._fetch_page_content(config['url'])
        if html:
            return await config['parser'](html, config)
        return []

    async def scrape_all(self):
        """Scrapes all configured news sources in parallel."""
        tasks = [self.scrape_source(name) for name in self.news_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_rumors = []
        for res in results:
            if isinstance(res, list):
                all_rumors.extend(res)
            elif isinstance(res, Exception):
                print(f"Error scraping a source: {res}")
        
        return all_rumors 