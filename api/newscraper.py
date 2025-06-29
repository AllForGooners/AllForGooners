import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from twikit import Client
import feedparser
from bs4 import BeautifulSoup, Tag

class NewsScraper:
    """
    Scrapes Arsenal news from various sources, including Twitter and RSS feeds.
    """
    def __init__(self):
        self.journalists = ["FabrizioRomano", "David_Ornstein"]
        self.rss_feeds = {
            "BBC Sport": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "Sky Sports": "https://www.skysports.com/rss/11095"
        }
        self.client = Client('en-US')
        # This list is essential for the RSS scraper to find general transfer news
        self.transfer_keywords = [
            'transfer', 'signing', 'signed', 'deal', 'bid', 'contract', 
            'talks', 'move', 'rumour', 'loan', 'join', 'fee agreed', 'here we go',
            '$', '€', '£', 'agree', 'sign'
        ]

    async def _login(self):
        """Logs into Twitter using credentials from environment variables."""
        if os.path.exists('cookies.json'):
            self.client.load_cookies('cookies.json')
            print("Successfully loaded cookies.")
        else:
            print("No cookie file found. Logging in with credentials...")
            load_dotenv()
            username = os.getenv("TWITTER_USERNAME")
            email = os.getenv("TWITTER_EMAIL")
            password = os.getenv("TWITTER_PASSWORD")

            # Assert that credentials are not None to satisfy the linter
            assert username is not None, "TWITTER_USERNAME not found in .env"
            assert email is not None, "TWITTER_EMAIL not found in .env"
            assert password is not None, "TWITTER_PASSWORD not found in .env"

            await self.client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password
            )
            self.client.save_cookies('cookies.json')
            print("Successfully logged in and saved cookies for future use.")

    def _get_image_from_tweet(self, tweet):
        """Extracts an image URL from a tweet's media, if available."""
        # First, try to get images from media attachments
        if hasattr(tweet, 'media') and tweet.media:
            for media_item in tweet.media:
                # Check for photo type media
                if hasattr(media_item, 'type') and media_item.type == 'photo':
                    if hasattr(media_item, 'media_url_https'):
                        # Get the highest quality image
                        image_url = media_item.media_url_https
                        # Remove size parameters for original size
                        if '?' in image_url:
                            image_url = image_url.split('?')[0]
                        return f"{image_url}?format=jpg&name=large"
        
        # If no media, try to extract from URLs in the tweet
        if hasattr(tweet, 'urls') and tweet.urls:
            for url_obj in tweet.urls:
                # Check if the URL is an image
                if hasattr(url_obj, 'expanded_url'):
                    url = url_obj.expanded_url
                    if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        return url
        
        # If all else fails, return None
        return None

    def _is_relevant_tweet(self, tweet):
        """Checks if a tweet is a relevant Arsenal story."""
        # We don't care about replies
        if tweet.reply_to:
            return False
            
        content_lower = (tweet.full_text).lower()
        is_arsenal_related = 'arsenal' in content_lower or '#afc' in content_lower
        
        # Check for transfer keywords to improve relevance
        transfer_keywords = ['transfer', 'sign', 'deal', 'bid', 'contract', 'talks', 'move']
        has_transfer_keyword = any(keyword in content_lower for keyword in transfer_keywords)
        
        # For testing purposes, be more lenient to get more results
        return is_arsenal_related  # Removed the AND condition to get more results

    async def _scrape_twitter_user(self, username):
        """Fetches and processes recent tweets for a single user."""
        print(f"Scraping tweets for {username}...")
        articles = []
        # Look back 7 days to have a better chance of finding relevant test tweets
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        try:
            user = await self.client.get_user_by_screen_name(username)
            # Fetch more tweets to ensure we see the history of very active users
            tweets = await user.get_tweets('Tweets', count=250) 
            
            for tweet in tweets:
                # Stop if tweets are older than the time window
                if tweet.created_at_datetime < seven_days_ago:
                    break

                if self._is_relevant_tweet(tweet):
                    image_url = self._get_image_from_tweet(tweet)
                    articles.append({
                        "headline": tweet.full_text,
                        "source_name": user.name,
                        "url": f"https://x.com/{user.screen_name}/status/{tweet.id}",
                        "content": tweet.full_text,
                        "image_url": image_url
                    })
        except Exception as e:
            print(f"Error scraping user {username}: {e}")
        
        print(f"Found {len(articles)} potential rumors from {username}.")
        return articles

    # --- RSS Feed Methods ---

    def _get_image_from_rss_entry(self, entry):
        """Attempts to find an image URL from various places in an RSS entry."""
        image_url = None
        
        # Debug the entry structure to see what's available
        print(f"Examining RSS entry: {entry.title}")
        
        # 1. Check for media_content (most reliable)
        if hasattr(entry, 'media_content') and entry.media_content:
            print(f"Found media_content in entry: {entry.title}")
            for media in entry.media_content:
                if media.get('medium') == 'image' and media.get('url'):
                    image_url = media.get('url')
                    print(f"Found image in media_content: {image_url}")
                    break
        
        # 2. Check for enclosures (another common pattern)
        if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
            print(f"Found enclosures in entry: {entry.title}")
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    image_url = enclosure.get('href')
                    print(f"Found image in enclosure: {image_url}")
                    break
        
        # 3. Check for media_thumbnail
        if not image_url and hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            print(f"Found media_thumbnail in entry: {entry.title}")
            image_url = entry.media_thumbnail[0].get('url')
            print(f"Found image in media_thumbnail: {image_url}")
        
        # 4. Fallback to parsing the summary HTML
        if not image_url and hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img_tag = soup.find('img')
            if isinstance(img_tag, Tag) and img_tag.get('src'):
                image_url = img_tag.get('src')
                print(f"Found image in summary HTML: {image_url}")
        
        # 5. Clean up BBC image URLs to get a higher resolution
        if image_url and isinstance(image_url, str) and 'bbci.co.uk' in image_url:
            try:
                # Use a more generic regex to handle different image sizes
                original_url = image_url
                image_url = re.sub(r'/cps/\d+/', '/cps/800/', image_url)
                print(f"Cleaned BBC image URL from {original_url} to {image_url}")
            except Exception as e:
                print(f"Error cleaning BBC image URL: {e}")
        
        # 6. Handle Sky Sports images to get higher resolution
        if image_url and isinstance(image_url, str) and 'skysports' in image_url:
            try:
                # For Sky Sports, try to get the highest quality version
                original_url = image_url
                if 'e=XXXLARGE' not in image_url:
                    image_url = re.sub(r'e=\w+', 'e=XXXLARGE', image_url)
                    print(f"Enhanced Sky Sports image URL from {original_url} to {image_url}")
            except Exception as e:
                print(f"Error enhancing Sky Sports image URL: {e}")
        
        # 7. Verify the image URL is valid
        if image_url:
            try:
                # Make sure the URL starts with http or https
                if isinstance(image_url, str) and not image_url.startswith(('http://', 'https://')):
                    if isinstance(image_url, str) and image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    else:
                        image_url = 'https://' + image_url
                print(f"Final image URL: {image_url}")
            except Exception as e:
                print(f"Error validating image URL: {e}")
        
        return image_url

    def _is_relevant_rss_entry(self, entry):
        """
        Checks if an RSS article is a relevant Arsenal transfer story.
        An article is relevant if it's about Arsenal OR it's a general transfer story.
        """
        content_lower = (entry.title + " " + entry.summary).lower()
        is_arsenal_related = 'arsenal' in content_lower
        has_transfer_keyword = any(keyword in content_lower for keyword in self.transfer_keywords)
        
        # We let the LLM do the final filtering, so we cast a wider net here.
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

    # --- Main Scraper Method ---
    async def scrape_all(self):
        """Logs in, scrapes all sources (Twitter and RSS), and returns combined articles."""
        # Scrape Twitter
        await self._login()
        twitter_articles = []
        for username in self.journalists:
            articles = await self._scrape_twitter_user(username)
            twitter_articles.extend(articles)
        print("Finished scraping Twitter feeds.")

        # Scrape RSS Feeds
        rss_articles = []
        for source_name, url in self.rss_feeds.items():
            # Running in a separate thread to avoid blocking asyncio event loop
            loop = asyncio.get_running_loop()
            articles = await loop.run_in_executor(
                None, self._scrape_rss_feed, source_name, url
            )
            rss_articles.extend(articles)
        print("Finished scraping RSS feeds.")
        
        return twitter_articles + rss_articles 