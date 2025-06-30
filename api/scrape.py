import os
import json
import asyncio
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from newscraper import NewsScraper
from llm_processor import process_with_llm
from sports_api_client import SportsApiClient

# --- CONFIGURATION ---
load_dotenv() # Load environment variables from .env file
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- IMAGE SEARCH FUNCTION ---
async def search_player_image(player_name):
    """
    Searches for a player image using the SportsApiClient.
    This provides a more reliable source for player headshots than generic search.
    """
    print(f"Initializing SportsApiClient to search for image of {player_name}...")
    try:
        client = SportsApiClient()
        # Using a hardcoded team_id for Arsenal (42) as this app is Arsenal-specific.
        image_url = await client.get_player_image(player_name, team_id=42)
        
        if image_url:
            return image_url
        else:
            print(f"SportsApiClient could not find an image for {player_name}.")
            return None

    except Exception as e:
        print(f"Error using SportsApiClient for {player_name}: {e}")
        return None

# --- ENHANCE ARTICLES WITH BETTER IMAGES ---
async def enhance_articles_with_images(processed_articles):
    """
    Enhances articles by searching for better player images when needed.
    """
    enhanced_articles = []
    
    for article in processed_articles:
        # If the article has no player name, skip enhancement
        if not article.get("player_name"):
            enhanced_articles.append(article)
            continue
            
        player_name = article["player_name"]
        
        # Check if we should search for a new image
        should_search_image = False
        
        # If no image_url or it's null/None, definitely search
        if not article.get("image_url") or article["image_url"] is None:
            should_search_image = True
            print(f"No image found for {player_name}, will search for one")
        
        # If we have an image but it contains generic terms, search for a better one
        elif isinstance(article["image_url"], str):
            generic_terms = ['logo', 'badge', 'stadium', 'generic', 'placeholder']
            if any(term in article["image_url"].lower() for term in generic_terms):
                should_search_image = True
                print(f"Found generic image for {player_name}, will search for a better one")
        
        # Search for a player-specific image if needed
        if should_search_image:
            print(f"Searching for image for {player_name}...")
            image_url = await search_player_image(player_name)
            if image_url:
                article["image_url"] = image_url
                print(f"Found image for {player_name}: {image_url}")
            else:
                print(f"Could not find image for {player_name}")
        
        enhanced_articles.append(article)
    
    return enhanced_articles

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

    # 5. Enhance articles with better images
    enhanced_articles = await enhance_articles_with_images(processed_articles)
    print(f"Enhanced {len(enhanced_articles)} articles with better images.")

    # 6. Save to Supabase
    if enhanced_articles:
        print("Saving processed articles to Supabase...")
        try:
            # 'upsert' will insert new rows or update existing ones if the player_name matches
            data, count = supabase.table('transfer_news').upsert(
                enhanced_articles, 
                on_conflict='player_name'
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