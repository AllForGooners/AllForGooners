import feedparser
import asyncio

class NewsScraper:
    """
    Scrapes Arsenal news from various RSS feeds.
    This is more reliable than direct web scraping as it uses official feeds.
    """
    def __init__(self):
        self.feeds = {
            "Fabrizio Romano": "https://rss.app/feed/7p2MgxJ88tQ3V35q",
            "David Ornstein": "https://rss.app/feed/Glfiywdo14rqxTEm",
            "Sky Sports": "https://www.skysports.com/rss/football/teams/arsenal"
        }

    async def _scrape_feed(self, source_name, url):
        """Parses a single RSS feed and returns a list of articles."""
        print(f"Scraping {source_name} from {url}...")
        articles = []
        try:
            # feedparser can handle both remote URLs and local file paths
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                # We only want entries related to Arsenal transfers
                content_lower = (entry.title + entry.summary).lower()
                if 'arsenal' in content_lower and 'transfer' in content_lower:
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