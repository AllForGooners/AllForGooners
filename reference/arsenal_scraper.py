#!/usr/bin/env python3
"""
Arsenal Transfer News Scraper
A comprehensive web scraping system for Arsenal FC transfer rumors

This module uses modern web scraping techniques to gather transfer news
from multiple sources, including news websites and Twitter, with robust
error handling and data processing.

Author: Gemini Pro @ Cursor
Date: 2024-05-21
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from twscrape import API
from twscrape.logger import set_log_level
from playwright.sync_api import sync_playwright

# --- Configuration ---
LOG_LEVEL = "INFO"
DATA_DIR = "arsenal-rumors-retro/data"
RUMORS_FILE = f"{DATA_DIR}/transfer-rumors.json"
SOCIAL_MEDIA_FILE = f"{DATA_DIR}/social-media-posts.json"

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
set_log_level(LOG_LEVEL)
logger = logging.getLogger(__name__)


# --- Data Structures ---

@dataclass
class TransferRumor:
    """Data structure for transfer rumors"""
    title: str
    source: str
    url: str
    timestamp: str
    content: str
    player_name: str = ""
    transfer_fee: str = ""
    reliability_score: int = 5
    rumor_type: str = "in"
    position: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SocialMediaPost:
    """Data structure for social media posts from twscrape"""
    content: str
    author: str
    author_handle: str
    timestamp: str
    url: str
    source: str = "Twitter"
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --- Scrapers ---

class NewsScraper:
    """Scrapes news websites for Arsenal transfer rumors."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.request_delay = 2
        self.last_request_time = 0
        self.news_sources = {
            'sky_sports': {
                'url': 'https://www.skysports.com/arsenal-news',
                'parser': self._parse_sky_sports,
                'reliability': 8
            },
        }

    def _rate_limit(self):
        """Ensures a delay between requests to be polite."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    def scrape_source(self, source_name: str) -> List[TransferRumor]:
        """Scrapes a single news source."""
        config = self.news_sources[source_name]
        if source_name == "sky_sports":
            html = fetch_skysports_with_playwright(config['url'])
            soup = BeautifulSoup(html, 'html.parser')
            return self._parse_sky_sports(soup, config)
        else:
            # For other sources, use requests as before
            self._rate_limit()
            try:
                response = self.session.get(config['url'], timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                return config['parser'](soup, config)
            except requests.RequestException as e:
                logger.error(f"Error scraping {source_name}: {e}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error scraping {source_name}: {e}")
                return []

    def _parse_sky_sports(self, soup: BeautifulSoup, config: dict) -> list:
        rumors = []
        for a in soup.select("a.sdc-site-tile__headline-link"):
            headline = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.skysports.com" + link
            rumors.append(TransferRumor(
                title=headline,
                source='Sky Sports',
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat(),
                content="",  # You can extract more if needed
                reliability_score=config['reliability']
            ))
        logger.info(f"Found {len(rumors)} potential rumors from Sky Sports.")
        return rumors

    def scrape_all(self) -> List[TransferRumor]:
        """Scrapes all configured news sources."""
        all_rumors = []
        for source_name in self.news_sources:
            all_rumors.extend(self.scrape_source(source_name))
        return all_rumors


class TwitterScraper:
    """Scrapes Twitter for journalist posts using twscrape."""

    def __init__(self, api: API):
        self.api = api
        self.journalists = {
            'FabrizioRomano': 'FabrizioRomano',
            'David_Ornstein': 'David_Ornstein',
        }

    async def scrape_journalist(self, username: str, limit: int = 10) -> List[SocialMediaPost]:
        """Scrapes a single journalist's recent tweets."""
        posts = []
        try:
            user = await self.api.user_by_login(self.journalists[username])
            if not user:
                logger.error(f"Could not find user for {username}")
                return posts
            user_id = user.id

            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=limit):
                tweets.append(tweet)
            for tweet in tweets:
                if "arsenal" in tweet.rawContent.lower() or "#afc" in tweet.rawContent.lower():
                    posts.append(SocialMediaPost(
                        content=tweet.rawContent,
                        author=tweet.user.displayname,
                        author_handle=tweet.user.username,
                        timestamp=tweet.date.isoformat(),
                        url=tweet.url,
                        likes=tweet.likeCount,
                        retweets=tweet.retweetCount,
                        replies=tweet.replyCount,
                        verified=tweet.user.verified
                    ))
            logger.info(f"Found {len(posts)} relevant tweets from @{username}.")
        except Exception as e:
            logger.error(f"Failed to scrape @{username}: {e}")
        return posts

    async def scrape_all(self) -> List[SocialMediaPost]:
        """Scrapes all configured journalists."""
        tasks = [self.scrape_journalist(name) for name in self.journalists]
        results = await asyncio.gather(*tasks)
        return [post for sublist in results for post in sublist]


# --- Data Management ---

def save_to_json(data: List[Dict], filename: str, key: str):
    """Saves a list of data to a JSON file."""
    logger.info(f"Saving {len(data)} items to {filename}")
    output = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        f'total_{key}': len(data),
        key: data
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# --- Main Orchestration ---

async def run_twitter_scraper():
    """Initializes and runs the Twitter scraper."""
    api = API()
    # Add your Twitter account here
    await api.pool.add_account("junkproof", "twitter1234", "junkproof@protonmail.com", "junkproof9999")
    await api.pool.login_all()
    
    scraper = TwitterScraper(api)
    posts = await scraper.scrape_all()
    save_to_json([p.to_dict() for p in posts], SOCIAL_MEDIA_FILE, 'posts')


def run_news_scraper():
    """Initializes and runs the news scraper."""
    scraper = NewsScraper()
    rumors = scraper.scrape_all()
    save_to_json([r.to_dict() for r in rumors], RUMORS_FILE, 'rumors')


def main():
    """Main function to run all scrapers."""
    logger.info("--- Starting Scraper Run ---")
    
    # Run news scraper (synchronous)
    run_news_scraper()
    
    # Run Twitter scraper (asynchronous)
    asyncio.run(run_twitter_scraper())
    
    logger.info("--- Scraper Run Finished ---")


def fetch_skysports_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        # Handle cookie consent in iframe
        for frame in page.frames:
            try:
                frame.wait_for_selector('button:has-text("Accept all")', timeout=5000)
                frame.click('button:has-text("Accept all")')
                break
            except Exception:
                continue
        page.wait_for_timeout(5000)  # Wait for content to load
        html = page.content()
        browser.close()
        return html


if __name__ == '__main__':
    main()
