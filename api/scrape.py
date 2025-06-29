import os
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from newscraper import NewsScraper
from llm_processor import process_with_llm

# --- CONFIGURATION ---
load_dotenv() # Load environment variables from .env file
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- ASYNC MAIN ---
async def main():
    # 1. Initialize Supabase client
    assert SUPABASE_URL, "SUPABASE_URL not found in environment variables."
    assert SUPABASE_SERVICE_KEY, "SUPABASE_SERVICE_KEY not found in environment variables."
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 2. Scrape News from RSS Feeds
    news_scraper = NewsScraper()
    raw_articles = await news_scraper.scrape_all()
    print(f"Scraped a total of {len(raw_articles)} raw articles.")

    # 3. Filter out articles already in the database
    if not raw_articles:
        print("No articles found to process.")
        return

    try:
        # Get all URLs currently in our database
        response = supabase.table('transfer_news').select('url').execute()
        existing_urls = {item['url'] for item in response.data}
        print(f"Found {len(existing_urls)} existing articles in the database.")
    except Exception as e:
        print(f"Warning: Could not fetch existing URLs from Supabase. May create duplicates. Error: {e}")
        existing_urls = set()

    # Keep only the articles that are not already in our database
    new_articles = [article for article in raw_articles if article['url'] not in existing_urls]
    
    print(f"Found {len(new_articles)} new articles to process.")

    if not new_articles:
        print("No new articles to process.")
        return

    # 4. Process with LLM via OpenRouter
    print("Processing content with LLM...")
    processed_articles = await process_with_llm(new_articles, OPENROUTER_API_KEY)
    print(f"LLM processing complete. {len(processed_articles)} articles ready for insertion.")

    # 5. Save to Supabase
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

# --- ENTRY POINT for direct execution ---
# This allows the script to be run from the command line by GitHub Actions
if __name__ == "__main__":
    print("Starting scheduled scrape task...")
    try:
        asyncio.run(main())
        print("Scraping and processing completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        # Exit with a non-zero status code to indicate failure to GitHub Actions
        exit(1)

# --- HELPER MODULES (to be created next) ---
# We will create the following files next:
# - newsscraper.py
# - twitterscraper.py
# - llm_processor.py
# - requirements.txt 