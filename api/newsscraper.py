import feedparser
import asyncio
from bs4 import BeautifulSoup

class NewsScraper:
    """
    Scrapes Arsenal news from various RSS feeds.
    This is more reliable than direct web scraping as it uses official feeds.
    """
    def __init__(self):
        self.feeds = {
            "BBC Sport": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "Sky Sports": "https://www.skysports.com/rss/11095"
        }
        self.transfer_keywords = [
            'transfer', 'signing', 'signed', 'deal', 'bid', 'contract', 
            'talks', 'move', 'rumour', 'loan', 'join', 'fee agreed', 'arsenal'
        ]

    def _get_image_from_entry(self, entry):
        """Attempts to find an image URL from various places in an RSS entry."""
        # Check for media_content (most common for modern feeds)
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' and media.get('url'):
                    return media.get('url')
        
        # Check for media_thumbnail as a fallback
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')

        # As a last resort, parse the summary HTML for an <img> tag
        if hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img_tag = soup.find('img')
            if img_tag and img_tag.has_attr('src'):
                return img_tag['src']
                
        return None # No image found

    def _is_relevant(self, entry, source_name):
        """Checks if an article is a relevant Arsenal transfer story."""
        content_lower = (entry.title + entry.summary).lower()

        # For these general football feeds, we must find "arsenal"
        if 'arsenal' not in content_lower:
            return False

        # And at least one transfer-related keyword
        return any(keyword in content_lower for keyword in self.transfer_keywords)

    async def _scrape_feed(self, source_name, url):
        """Parses a single RSS feed and returns a list of relevant articles."""
        print(f"Scraping {source_name} from {url}...")
        articles = []
        try:
            # Add a common browser User-Agent to prevent being blocked
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            feed = feedparser.parse(url, agent=user_agent)

            # --- DIAGNOSTIC CHECK ---
            if feed.bozo:
                print(f"  [WARNING] Feed for {source_name} is not well-formed. Reason: {feed.bozo_exception}")
            
            if not feed.entries:
                print(f"  [INFO] Feed for {source_name} has 0 entries. Status: {feed.get('status', 'N/A')}")
            # --- END DIAGNOSTIC ---

            for entry in feed.entries:
                if self._is_relevant(entry, source_name):
                    image_url = self._get_image_from_entry(entry)
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
        """Scrapes all configured RSS feeds in parallel."""
        tasks = []
        for source_name, url in self.feeds.items():
            tasks.append(self._scrape_feed(source_name, url))
        
        results = await asyncio.gather(*tasks)
        
        # Flatten the list of lists into a single list of articles
        all_articles = [article for result in results for article in result]
        return all_articles

if __name__ == '__main__':
    # Example of how to run the scraper for testing
    async def test_scraper():
        scraper = NewsScraper()
        articles = await scraper.scrape_all()
        print(f"\n--- Total Articles Found: {len(articles)} ---")
        for article in articles:
            print(f"  - [{article['source_name']}] {article['headline']}")
    
    asyncio.run(test_scraper()) 