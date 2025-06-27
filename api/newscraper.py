import feedparser
import asyncio
import re
from bs4 import BeautifulSoup

class NewsScraper:
    """
    Scrapes Arsenal news from various RSS feeds.
    This is more reliable than direct web scraping as it uses official feeds.
    """
    def __init__(self):
        self.feeds = {
            "Fabrizio Romano": "https://nitter.net/FabrizioRomano/rss",
            "David Ornstein": "https://nitter.net/David_Ornstein/rss",
            "BBC Sport": "http://feeds.bbci.co.uk/sport/football/rss.xml"
        }
        self.transfer_keywords = [
            'transfer', 'signing', 'signed', 'deal', 'bid', 'contract', 
            'talks', 'move', 'rumour', 'loan', 'join', 'fee agreed'
        ]

    def _get_image_from_entry(self, entry):
        """Attempts to find an image URL from various places in an RSS entry."""
        image_url = None
        # Check for media_content (most common for modern feeds)
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' and media.get('url'):
                    image_url = media.get('url')
                    break
        
        # Check for media_thumbnail as a fallback
        if not image_url and hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get('url')

        # As a last resort, parse the summary HTML for an <img> tag
        if not image_url and hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img_tag = soup.find('img')
            if img_tag and img_tag.has_attr('src'):
                image_url = img_tag['src']

        # If we found a BBC image, try to get a higher resolution version
        if image_url and 'bbci.co.uk' in image_url:
            try:
                # e.g., .../cps/480/... becomes .../cps/976/...
                image_url = re.sub(r'/cps/\d+/', '/cps/976/', image_url)
            except Exception:
                pass # If regex fails, use the original URL
                
        return image_url

    def _is_relevant(self, entry, source_name):
        """Checks if an article is a relevant Arsenal transfer story."""
        content_lower = (entry.title + entry.summary).lower()

        # For journalists, we are more lenient and check for "arsenal" or "#afc"
        if source_name in ["Fabrizio Romano", "David Ornstein"]:
            is_relevant_tweet = 'arsenal' in content_lower or '#afc' in content_lower
            if is_relevant_tweet:
                print(f"[DEBUG] Found relevant tweet from {source_name}: {entry.title}")
            return is_relevant_tweet

        # For news sites, we need "arsenal" AND a transfer keyword
        if 'arsenal' in content_lower:
            return any(keyword in content_lower for keyword in self.transfer_keywords)
            
        return False

    async def _scrape_feed(self, source_name, url):
        """Parses a single RSS feed and returns a list of relevant articles."""
        print(f"Scraping {source_name} from {url}...")
        articles = []
        try:
            # Add a common browser User-Agent to prevent being blocked
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            feed = feedparser.parse(url, agent=user_agent)

            for entry in feed.entries:
                if self._is_relevant(entry, source_name):
                    articles.append({
                        "headline": entry.title,
                        "source_name": source_name,
                        "url": entry.link,
                        "content": entry.summary,
                    })
        except Exception as e:
            print(f"Error scraping feed {source_name}: {e}")

        print(f"Found {len(articles)} potential rumors from {source_name}.")
        return articles

    async def scrape_all(self):
        """Scrapes all feeds and returns a list of all relevant articles."""
        all_articles = []
        for source_name, url in self.feeds.items():
            articles = await self._scrape_feed(source_name, url)
            all_articles.extend(articles)
        return all_articles 