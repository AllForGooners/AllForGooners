import httpx
import re
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import quote

class TweetFinder:
    """
    A class to find relevant tweets without requiring Twitter authentication.
    Uses public web scraping techniques to find tweets.
    """
    
    def __init__(self):
        self.journalists = ["FabrizioRomano", "David_Ornstein"]
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
    async def find_all_relevant_tweets(self):
        """Finds relevant tweets from all configured journalists."""
        all_tweets = []
        for username in self.journalists:
            tweets = await self._find_tweets_for_user(username)
            all_tweets.extend(tweets)
        return all_tweets
        
    async def _find_tweets_for_user(self, username):
        """
        Finds relevant tweets for a specific user by scraping Twitter's public web interface.
        No authentication required.
        """
        print(f"Finding tweets for {username}...")
        tweets = []
        
        # Method 1: Scrape Twitter's advanced search results
        # This uses Twitter's public search page which doesn't require login
        search_query = f"from:{username} arsenal OR #afc"
        encoded_query = quote(search_query)
        search_url = f"https://twitter.com/search?q={encoded_query}&src=typed_query&f=live"
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {"User-Agent": self.user_agent}
                response = await client.get(search_url, headers=headers)
                
                if response.status_code == 200:
                    # Parse the HTML to extract tweet IDs
                    # Note: Twitter's web interface uses JavaScript to load content
                    # This basic approach might not work without additional techniques
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tweet_elements = soup.select('[data-testid="tweet"]')
                    
                    for element in tweet_elements:
                        # Extract tweet ID from the element
                        # This is a simplified example and might need adjustment
                        links = element.select('a[href*="/status/"]')
                        for link in links:
                            href = link.get('href', '')
                            match = re.search(r'/status/(\d+)', href)
                            if match:
                                tweet_id = match.group(1)
                                tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
                                
                                # Get tweet text if available
                                text_element = element.select_one('[data-testid="tweetText"]')
                                tweet_text = text_element.get_text() if text_element else ""
                                
                                if self._is_relevant_tweet_text(tweet_text):
                                    tweets.append({
                                        "url": tweet_url,
                                        "source_name": username,
                                        "headline": tweet_text[:100],
                                        "content": tweet_text
                                    })
                else:
                    print(f"Failed to fetch tweets for {username}: HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"Error finding tweets for {username}: {e}")
        
        # Method 2: Use a public API aggregator (if available)
        # This would be implemented here if you find a suitable service
        
        return tweets
    
    def _is_relevant_tweet_text(self, text):
        """Checks if a tweet is relevant based on its text content."""
        if not text:
            return False
            
        text_lower = text.lower()
        is_arsenal_related = 'arsenal' in text_lower or '#afc' in text_lower
        
        # Check for transfer keywords to improve relevance
        transfer_keywords = ['transfer', 'sign', 'deal', 'bid', 'contract', 'talks', 'move']
        has_transfer_keyword = any(keyword in text_lower for keyword in transfer_keywords)
        
        # For testing purposes, be more lenient to get more results
        return is_arsenal_related  # You could add "and has_transfer_keyword" to be more strict

# Example usage
async def main():
    finder = TweetFinder()
    tweets = await finder.find_all_relevant_tweets()
    print(f"Found {len(tweets)} relevant tweets")
    for tweet in tweets[:5]:  # Print first 5 tweets
        print(f"- {tweet['url']}: {tweet['headline']}")

if __name__ == "__main__":
    asyncio.run(main()) 