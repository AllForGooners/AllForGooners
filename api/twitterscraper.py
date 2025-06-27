import asyncio
from twscrape import API
from twscrape.logger import set_log_level

class TwitterScraper:
    """Scrapes Twitter for journalist posts using twscrape."""

    def __init__(self):
        self.api = API()
        self.journalists = [
            'FabrizioRomano',
            'David_Ornstein',
            # Add other journalist usernames here
        ]

    async def _login_accounts(self):
        """Pools accounts from accounts.json to avoid rate limits."""
        # You must create an 'accounts.json' file in the format:
        # [
        #   ["user1", "pass1", "email1", "email_pass1"],
        #   ["user2", "pass2", "email2", "email_pass2"]
        # ]
        # This is necessary for twscrape to work reliably.
        try:
            await self.api.pool.load_from_file("api/accounts.json", line_format="user:pass:email:email_pass")
            await self.api.pool.login_all()
            print(f"Successfully logged in {len(self.api.pool.accounts)} Twitter accounts.")
        except Exception as e:
            print(f"Could not log in to Twitter accounts. Please check accounts.json. Error: {e}")
            # Continue without login, but it's likely to fail
            pass

    async def scrape_journalist(self, username, limit=20):
        """Scrapes a single journalist's recent tweets for Arsenal news."""
        posts = []
        try:
            # Note: user_tweets is an async generator
            async for tweet in self.api.user_tweets(username, limit=limit):
                is_arsenal_related = "arsenal" in tweet.rawContent.lower() or "#afc" in tweet.rawContent.lower()
                if is_arsenal_related:
                    posts.append({
                        "headline": f"Tweet by @{tweet.user.username}",
                        "source_name": "X (Twitter)",
                        "url": tweet.url,
                        "content": tweet.rawContent
                    })
            print(f"Found {len(posts)} relevant tweets from @{username}.")
        except Exception as e:
            print(f"Failed to scrape @{username}: {e}")
        return posts

    async def scrape_all(self):
        """Scrapes all configured journalists in parallel."""
        # Login is critical for scraping X
        await self._login_accounts()
        
        tasks = [self.scrape_journalist(name) for name in self.journalists]
        results = await asyncio.gather(*tasks) # Use asyncio.gather
        
        all_posts = []
        for res in results:
            if isinstance(res, list):
                all_posts.extend(res)
        
        return all_posts 