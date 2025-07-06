#!/usr/bin/env python3
"""
Test script for verifying the Nitter integration with the scraper.
This script checks if:
1. The Nitter instance is accessible
2. The RSS feeds can be successfully scraped
3. Tweet content is properly parsed and cleaned
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv
import httpx

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.newscraper import NewsScraper

async def detailed_nitter_diagnostics(url):
    """Perform detailed diagnostics on the Nitter instance."""
    print(f"\n=== Detailed Nitter Diagnostics for {url} ===")
    
    # Test base URL
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"Testing base URL: {url}")
            response = await client.get(url)
            print(f"Status code: {response.status_code}")
            print(f"Content type: {response.headers.get('content-type')}")
            if response.status_code == 200:
                print("✓ Base URL is accessible")
            else:
                print(f"✗ Base URL returned status code {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing base URL: {e}")
    
    # Test RSS endpoint
    try:
        rss_url = f"{url}/FabrizioRomano/rss"
        print(f"\nTesting RSS endpoint: {rss_url}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(rss_url)
            print(f"Status code: {response.status_code}")
            print(f"Content type: {response.headers.get('content-type')}")
            if response.status_code == 200:
                if 'application/rss+xml' in response.headers.get('content-type', ''):
                    print("✓ RSS endpoint is returning proper XML")
                else:
                    print(f"✗ RSS endpoint is not returning XML (got {response.headers.get('content-type')})")
                    print("First 200 characters of response:")
                    print(response.text[:200])
            else:
                print(f"✗ RSS endpoint returned status code {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing RSS endpoint: {e}")
    
    # Test a profile page
    try:
        profile_url = f"{url}/FabrizioRomano"
        print(f"\nTesting profile page: {profile_url}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(profile_url)
            print(f"Status code: {response.status_code}")
            print(f"Content type: {response.headers.get('content-type')}")
            if response.status_code == 200:
                print("✓ Profile page is accessible")
            else:
                print(f"✗ Profile page returned status code {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing profile page: {e}")

async def test_nitter_connection():
    """Test if the Nitter instance is accessible."""
    try:
        scraper = NewsScraper()
        print(f"\n✓ Successfully initialized scraper with Nitter URL: {scraper.nitter_url}")
        
        # Run detailed diagnostics
        await detailed_nitter_diagnostics(scraper.nitter_url)
        
        # Test connection to Nitter
        nitter_status = await scraper.check_nitter_status()
        if nitter_status:
            print(f"✓ Successfully connected to Nitter instance: {scraper.nitter_url}")
        else:
            print(f"✗ Failed to connect to Nitter instance: {scraper.nitter_url}")
            print("  Please check if the Nitter instance is running and accessible.")
            return False
        return True
    except Exception as e:
        print(f"✗ Error initializing scraper: {e}")
        return False

async def test_nitter_feeds():
    """Test if Nitter RSS feeds can be scraped."""
    try:
        scraper = NewsScraper()
        
        # Get list of Nitter feeds
        nitter_feeds = {name: url for name, url in scraper.rss_feeds.items() 
                      if scraper._is_nitter_feed(url)}
        
        print(f"\nFound {len(nitter_feeds)} Nitter feeds to test:")
        for name, url in nitter_feeds.items():
            print(f"  - {name}: {url}")
        
        if not nitter_feeds:
            print("✗ No Nitter feeds found. Check that your Nitter URL is configured correctly.")
            return False
        
        # Test each feed
        print("\nTesting individual Nitter feeds:")
        all_successful = True
        for name, url in nitter_feeds.items():
            print(f"\nTesting feed: {name}")
            articles = scraper._scrape_rss_feed(name, url)
            
            if articles:
                print(f"✓ Successfully scraped {len(articles)} articles from {name}")
                # Print sample article
                if articles:
                    print("\nSample article:")
                    sample = articles[0]
                    print(f"  Headline: {sample['headline']}")
                    print(f"  Content (first 100 chars): {sample['content'][:100]}...")
                    print(f"  Is tweet: {sample['is_tweet']}")
                    if sample['image_url']:
                        print(f"  Image URL: {sample['image_url']}")
                    else:
                        print("  No image found")
            else:
                print(f"✗ Failed to scrape any articles from {name}")
                all_successful = False
        
        return all_successful
    except Exception as e:
        print(f"✗ Error testing Nitter feeds: {e}")
        return False

async def test_full_scrape():
    """Test the full scraping process with all feeds."""
    try:
        print("\nTesting full scrape process (all feeds):")
        scraper = NewsScraper()
        articles = await scraper.scrape_all()
        
        if articles:
            print(f"✓ Successfully scraped {len(articles)} articles in total")
            
            # Count tweets vs other articles
            tweets = [a for a in articles if a.get('is_tweet')]
            print(f"  - Tweets: {len(tweets)}")
            print(f"  - News articles: {len(articles) - len(tweets)}")
            
            return True
        else:
            print("✗ Failed to scrape any articles")
            return False
    except Exception as e:
        print(f"✗ Error during full scrape: {e}")
        return False

async def main():
    """Run all tests."""
    print("=== Nitter Integration Test ===")
    
    # Test 1: Connection
    connection_ok = await test_nitter_connection()
    if not connection_ok:
        print("\n✗ Connection test failed. Cannot proceed with further tests.")
        return False
    
    # Test 2: Nitter feeds
    feeds_ok = await test_nitter_feeds()
    
    # Test 3: Full scrape
    scrape_ok = await test_full_scrape()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Connection test: {'✓ Passed' if connection_ok else '✗ Failed'}")
    print(f"Nitter feeds test: {'✓ Passed' if feeds_ok else '✗ Failed'}")
    print(f"Full scrape test: {'✓ Passed' if scrape_ok else '✗ Failed'}")
    
    if connection_ok and feeds_ok and scrape_ok:
        print("\n✓ All tests passed! Nitter integration is working correctly.")
        return True
    else:
        print("\n✗ Some tests failed. Please check the logs above for details.")
        return False

if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    
    # Check if NITTER_URL is set
    if not os.getenv("NITTER_URL"):
        print("Error: NITTER_URL environment variable is not set.")
        print("Please set it in your .env file or environment variables.")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(main())
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 