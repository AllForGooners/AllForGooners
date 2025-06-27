import os
import json
import asyncio
from datetime import datetime, timezone
from supabase import create_client, Client
from newsscraper import NewsScraper
from twitterscraper import TwitterScraper
from llm_processor import process_with_llm

# --- CONFIGURATION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- MAIN HANDLER for Vercel ---
# Vercel will call this function when the cron job runs.
def handler(request, response):
    print("Starting scheduled scrape task...")
    try:
        # Run the main async function
        asyncio.run(main())
        
        # Send success response
        response.status_code = 200
        response.send("Scraping and processing completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        # Send error response
        response.status_code = 500
        response.send(f"An error occurred: {str(e)}")

# --- ASYNC MAIN ---
async def main():
    # 1. Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 2. Scrape News and Twitter
    news_scraper = NewsScraper()
    twitter_scraper = TwitterScraper()

    # Run scrapers in parallel
    scraped_news_task = asyncio.create_task(news_scraper.scrape_all())
    scraped_tweets_task = asyncio.create_task(twitter_scraper.scrape_all())

    raw_news = await scraped_news_task
    raw_tweets = await scraped_tweets_task
    
    # Combine raw data
    raw_articles = raw_news + raw_tweets
    print(f"Scraped a total of {len(raw_articles)} raw articles/tweets.")

    if not raw_articles:
        print("No articles found to process.")
        return

    # 3. Process with LLM via OpenRouter
    print("Processing content with LLM...")
    processed_articles = await process_with_llm(raw_articles, OPENROUTER_API_KEY)
    print(f"LLM processing complete. {len(processed_articles)} articles ready for insertion.")

    # 4. Save to Supabase
    if processed_articles:
        print("Saving processed articles to Supabase...")
        try:
            # 'upsert' will insert new rows or update existing ones if the headline matches
            data, count = supabase.table('transfer_news').upsert(
                processed_articles, 
                on_conflict='headline'
            ).execute()
            print(f"Successfully upserted {len(data[1])} articles into Supabase.")
        except Exception as e:
            print(f"Error saving to Supabase: {e}")
            raise
    
    print("Scraping task finished.")

# --- HELPER MODULES (to be created next) ---
# We will create the following files next:
# - newsscraper.py
# - twitterscraper.py
# - llm_processor.py
# - requirements.txt 