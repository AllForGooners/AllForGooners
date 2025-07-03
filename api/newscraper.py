import asyncio
import os
import re
from dotenv import load_dotenv
import feedparser
from bs4 import BeautifulSoup, Tag

class NewsScraper:
    """
    Scrapes Arsenal news from various sources, now using Nitter for Twitter feeds
    and traditional RSS feeds.
    """
    def __init__(self):
        """
        Initializes the NewsScraper, configuring RSS feeds including Nitter.
        """
        load_dotenv()
        nitter_url = os.getenv("NITTER_URL")
        if not nitter_url:
            raise ValueError("NITTER_URL environment variable not set. Please configure it in your .env file.")

        journalists = ["FabrizioRomano", "David_Ornstein"]
        
        self.rss_feeds = {
            "BBC Sport": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "Sky Sports": "https://www.skysports.com/rss/11095"
        }

        for user in journalists:
            self.rss_feeds[user] = f"{nitter_url}/{user}/rss"

        self.transfer_keywords = [
            'transfer', 'signing', 'signed', 'deal', 'bid', 'contract', 
            'talks', 'move', 'rumour', 'loan', 'join', 'fee agreed', 'here we go',
            '$', '€', '£', 'agree', 'sign'
        ]

    def _get_image_from_rss_entry(self, entry):
        """Attempts to find an image URL from various places in an RSS entry."""
        image_url = None
        
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
        
        if not image_url and hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get('url')
        
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
                if isinstance(image_url, str) and image_url.startswith('//'):
                    image_url = 'https:' + image_url
                else:
                    image_url = 'https://' + image_url
        
        return image_url

    def _is_relevant_rss_entry(self, entry):
        """
        Checks if an RSS article is a relevant Arsenal transfer story.
        """
        content_lower = (entry.title + " " + entry.summary).lower()
        is_arsenal_related = 'arsenal' in content_lower
        has_transfer_keyword = any(keyword in content_lower for keyword in self.transfer_keywords)
        
        return is_arsenal_related or has_transfer_keyword

    def _scrape_rss_feed(self, source_name, url):
        """Parses a single RSS feed and returns a list of relevant articles."""
        print(f"Scraping {source_name} from {url}...")
        articles = []
        try:
            user_agent = "AllForGooners/1.0 (RSSScraper; +https://all-for-gooners.vercel.app/)"
            feed = feedparser.parse(url, agent=user_agent)

            for entry in feed.entries:
                if self._is_relevant_rss_entry(entry):
                    image_url = self._get_image_from_rss_entry(entry)
                    articles.append({
                        "headline": entry.title,
                        "source_name": source_name,
                        "url": entry.link,
                        "content": entry.summary,
                        "image_url": image_url
                    })
        except Exception as e:
            print(f"Error scraping feed {source_name}: {e}")
        
        print(f"Found {len(articles)} potential rumors from {source_name}.")
        return articles

    async def scrape_all(self):
        """Scrapes all configured RSS feeds (including Nitter) concurrently."""
        loop = asyncio.get_running_loop()
        tasks = []
        for source_name, url in self.rss_feeds.items():
            task = loop.run_in_executor(
                None, self._scrape_rss_feed, source_name, url
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        
        all_articles = [article for feed_articles in results for article in feed_articles]
        
        print(f"Finished scraping all feeds. Found a total of {len(all_articles)} articles.")
        return all_articles