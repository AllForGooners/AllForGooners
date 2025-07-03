import os
import sys
import asyncio

# Change to the root directory
root_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(root_dir)
print(f"Working directory set to: {os.getcwd()}")

# Add the api directory to the path
sys.path.insert(0, os.path.join(root_dir, 'api'))

# Import and run the scraper
from api.scrape import main

if __name__ == "__main__":
    print("Starting scraper from wrapper...")
    try:
        asyncio.run(main())
        print("Scraping completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1) 