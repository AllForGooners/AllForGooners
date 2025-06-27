import feedparser
import asyncio

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

    def _is_relevant(self, entry, source_name):
        """Checks if an article is a relevant Arsenal transfer story."""
        content_lower = (entry.title + entry.summary).lower()

        # For journalists, we only need the keyword "arsenal"
        if source_name in ["Fabrizio Romano", "David Ornstein"]:
            return 'arsenal' in content_lower

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