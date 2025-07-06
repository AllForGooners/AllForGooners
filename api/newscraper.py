import asyncio
import os
import re
import time
from typing import Dict, List, Optional, Any, Union, cast
from urllib.parse import urlparse

from dotenv import load_dotenv
import feedparser
import httpx
from bs4 import BeautifulSoup, Tag

class NewsScraper:
    """
    Scrapes Arsenal news from various sources, using Nitter for Twitter feeds
    and traditional RSS feeds with robust error handling and retry logic.
    """
    def __init__(self):
        """
        Initializes the NewsScraper, configuring RSS feeds including Nitter.
        """
        load_dotenv()
        nitter_url = os.getenv("NITTER_URL")
        if not nitter_url:
            raise ValueError("NITTER_URL environment variable not set. Please configure it in your .env file.")
        
        # Ensure the URL doesn't have a trailing slash
        nitter_url = nitter_url.rstrip('/')
        self.nitter_url = nitter_url
        
        # Validate the Nitter URL format
        parsed_url = urlparse(nitter_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid NITTER_URL format: {nitter_url}. URL must include scheme (http:// or https://) and domain.")

        # Football journalists to follow
        journalists = ["FabrizioRomano", "David_Ornstein"]
        
        # Traditional RSS feeds
        self.rss_feeds = {
            "BBC Sport": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "Sky Sports": "https://www.skysports.com/rss/11095"
        }

        # Nitter RSS feeds
        for user in journalists:
            self.rss_feeds[user] = f"{nitter_url}/{user}/rss"

        # Transfer-related keywords to filter content
        self.transfer_keywords = [
            'transfer', 'signing', 'signed', 'deal', 'bid', 'contract', 
            'talks', 'move', 'rumour', 'loan', 'join', 'fee agreed', 'here we go',
            '$', '€', '£', 'agree', 'sign'
        ]
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # Initial delay in seconds
        
        # User agent to identify requests
        self.user_agent = "AllForGooners/1.0 (RSSScraper; +https://all-for-gooners.vercel.app/)"

    def _get_image_from_rss_entry(self, entry: Any) -> Optional[str]:
        """Attempts to find an image URL from various places in an RSS entry."""
        image_url: Optional[str] = None
        
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' and media.get('url'):
                    image_url = media.get('url')
                    break
        
        if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    image_url = enclosure.get('href')
                    break
        
        # Handle media thumbnails with better type safety
        if not image_url and hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            try:
                if hasattr(entry.media_thumbnail[0], 'get'):
                    url = entry.media_thumbnail[0].get('url')
                    if isinstance(url, str):
                        image_url = url
            except (IndexError, AttributeError, TypeError):
                pass
        
        if not image_url and hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img_tag = soup.find('img')
            if isinstance(img_tag, Tag) and img_tag.get('src'):
                image_url = img_tag.get('src')
        
        if image_url and isinstance(image_url, str) and 'bbci.co.uk' in image_url:
            image_url = re.sub(r'/cps/\d+/', '/cps/800/', image_url)
        
        if image_url and isinstance(image_url, str) and 'skysports' in image_url:
            if 'e=XXXLARGE' not in image_url:
                image_url = re.sub(r'e=\w+', 'e=XXXLARGE', image_url)
        
        if image_url:
            if isinstance(image_url, str) and not image_url.startswith(('http://', 'https://')):
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                else:
                    image_url = 'https://' + image_url
        
        return image_url

    def _is_relevant_rss_entry(self, entry: Any) -> bool:
        """
        Checks if an RSS article is a relevant Arsenal transfer story.
        """
        content_lower = (entry.title + " " + getattr(entry, 'summary', '')).lower()
        is_arsenal_related = 'arsenal' in content_lower
        has_transfer_keyword = any(keyword in content_lower for keyword in self.transfer_keywords)
        
        return is_arsenal_related or has_transfer_keyword

    def _clean_tweet_content(self, content: str) -> str:
        """
        Cleans tweet content from Nitter RSS feed to make it more readable.
        """
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Fix common Twitter-specific formatting issues
        text = text.replace('&amp;', '&')
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove URLs at the end (typically shortened t.co links)
        text = re.sub(r'https://t\.co/\w+$', '', text)
        
        return text.strip()

    def _is_nitter_feed(self, url: str) -> bool:
        """Checks if a feed URL is from Nitter."""
        return self.nitter_url in url

    def _scrape_rss_feed_with_retry(self, source_name: str, url: str) -> List[Dict[str, Any]]:
        """Scrapes an RSS feed with retry logic."""
        articles = []
        retry_count = 0
        delay = self.retry_delay
        
        while retry_count <= self.max_retries:
            try:
                print(f"Scraping {source_name} from {url}... (Attempt {retry_count + 1})")
                
                feed = feedparser.parse(url, agent=self.user_agent)
                
                if not hasattr(feed, 'entries') or not feed.entries:
                    if self._is_nitter_feed(url) and hasattr(feed, 'bozo_exception'):
                        print(f"Nitter feed error for {source_name}: {feed.bozo_exception}")
                        raise Exception(f"Nitter feed error: {feed.bozo_exception}")
                    elif not feed.entries:
                        print(f"No entries found in feed {source_name}")
                        return articles
                
                is_nitter = self._is_nitter_feed(url)
                
                for entry in feed.entries:
                    if self._is_relevant_rss_entry(entry):
                        image_url = self._get_image_from_rss_entry(entry)
                        
                        content = getattr(entry, 'summary', '')
                        if is_nitter and isinstance(content, str):
                            content = self._clean_tweet_content(content)
                        elif not isinstance(content, str):
                            content = str(content)
                        
                        articles.append({
                            "headline": entry.title,
                            "source_name": source_name,
                            "url": entry.link,
                            "content": content,
                            "image_url": image_url,
                            "is_tweet": is_nitter
                        })
                
                print(f"Found {len(articles)} potential rumors from {source_name}.")
                return articles
                
            except Exception as e:
                retry_count += 1
                print(f"Error scraping feed {source_name} (Attempt {retry_count}/{self.max_retries}): {e}")
                
                if retry_count <= self.max_retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print(f"Max retries reached for {source_name}. Moving on.")
                    return articles
        
        return articles

    async def check_nitter_status(self) -> bool:
        """
        Checks if the Nitter instance is responding properly.
        Returns True if healthy, False if there are issues.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to access the base URL first
                response = await client.get(self.nitter_url)
                if response.status_code != 200:
                    print(f"Nitter base URL returned status code {response.status_code}")
                    return False
                
                # Try to access a profile page
                profile_url = f"{self.nitter_url}/FabrizioRomano"
                response = await client.get(profile_url)
                if response.status_code != 200:
                    print(f"Nitter profile page returned status code {response.status_code}")
                    return False
                    
                # Try to access the RSS feed directly
                rss_url = f"{self.nitter_url}/FabrizioRomano/rss"
                response = await client.get(rss_url)
                if response.status_code != 200:
                    print(f"Nitter RSS feed returned status code {response.status_code}")
                    return False
                
                # Check if the RSS feed is actually XML
                content_type = response.headers.get('content-type', '')
                if isinstance(content_type, list):
                    content_type = content_type[0] if content_type else ''
                if 'xml' not in content_type.lower():
                    print(f"Nitter RSS feed returned non-XML content type: {content_type}")
                    return False
                
                return True
        except Exception as e:
            print(f"Nitter health check failed: {e}")
            return False

    def _scrape_rss_feed(self, source_name: str, url: str) -> List[Dict[str, Any]]:
        """Legacy wrapper for the retry version."""
        return self._scrape_rss_feed_with_retry(source_name, url)

    async def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrapes all configured RSS feeds (including Nitter) concurrently."""
        # First check if Nitter is responding
        nitter_status = await self.check_nitter_status()
        if not nitter_status:
            print("WARNING: Nitter instance appears to be down. Twitter feeds may fail.")
        
        loop = asyncio.get_running_loop()
        tasks = []
        for source_name, url in self.rss_feeds.items():
            # Skip Nitter feeds if Nitter is down
            if not nitter_status and self._is_nitter_feed(url):
                print(f"Skipping {source_name} due to Nitter being unreachable")
                continue
                
            task = loop.run_in_executor(
                None, self._scrape_rss_feed, source_name, url
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        all_articles = []
        for i, result in enumerate(results):
            source_name = list(self.rss_feeds.keys())[i]
            if isinstance(result, Exception):
                print(f"Error scraping {source_name}: {result}")
            else:
                articles = cast(List[Dict[str, Any]], result)
                all_articles.extend(articles)
        
        print(f"Finished scraping all feeds. Found a total of {len(all_articles)} articles.")
        return all_articles