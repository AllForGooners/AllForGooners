# All For Gooners - Project Roadmap

This document outlines the current state of the project and the strategic roadmap for future development.

---

### **Current System Architecture & State**

#### Full Stack Overview
*   **Backend:** Python (`asyncio`, `httpx`, `feedparser`)
*   **Data Processing:** LLM orchestration via OpenRouter
*   **Database:** Supabase (PostgreSQL)
*   **Frontend:** Vanilla JavaScript, HTML5, CSS3
*   **Containerization:** Docker, Docker Compose
*   **Deployment:** Main application on Vercel (serverless); Services (e.g., Nitter) on Northflank.

#### Component Breakdown

*   **Data Ingestion (`api/newscraper.py`):**
    *   **RSS Feeds (Stable):** Utilizes `feedparser` for reliable data extraction from BBC Sport and Sky Sports. This component is functional and considered production-ready.
    *   **Twitter/X Scraping (New Architecture):** The legacy `twikit` implementation is being replaced by a private, self-hosted Nitter instance running in Docker. This provides a stable, reliable, and isolated service for scraping tweets, removing the dependency on brittle, reverse-engineered libraries.

*   **Orchestration & State Management (`api/scrape.py`):**
    *   The core orchestrator, `api/scrape.py`, runs an `asyncio` event loop, managing the full ETL pipeline.
    *   State is managed via Supabase; the pipeline performs URL-based deduplication against the `transfer_news` table before processing to ensure idempotency and prevent redundant LLM calls.

*   **NLP & Data Processing (`api/llm_processor.py`):**
    *   Leverages OpenRouter to interface with multiple Large Language Models for advanced NLP tasks, including transfer-specific filtering, entity extraction (player names), and content summarization.
    *   The implementation is robust, featuring a fallback mechanism across a list of preferred models to mitigate rate-limiting issues and ensure high availability.

*   **Image Enhancement (`api/scrape.py`):**
    *   The `enhance_articles_with_images` function is currently a stub. The previous implementation has been removed, creating a clear entry point for integrating dedicated sports APIs for image retrieval—a key piece of technical debt to be addressed.

*   **Data Persistence & Frontend (`Supabase` & `frontend/`):**
    *   Processed and structured data is persisted to a Supabase PostgreSQL instance.
    *   The vanilla JS frontend (`frontend/js/main.js`) directly queries the Supabase API to dynamically render content. This decouples the frontend from the backend processing pipeline.

*   **API & Configuration:**
    *   Configuration is managed via a standard `.env` file.
    *   The project holds recently acquired, **unintegrated** API credentials for API-Football, SportMonks, and the Wikimedia API. These assets are critical for the next phase of development.

---

### **Project Development Roadmap**

## Phase 1: UI/UX Overhaul & Backend Refactoring

*   **Objective:** To deliver a polished, modern, and highly usable frontend experience based on the v1.0 plan, establishing a strong visual identity for the application. This will be followed by refactoring the backend to improve stability and maintainability.
*   **Key Initiatives:**
    1.  **Implement Final v1.0 Frontend Plan (Top Priority):**
        *   **Header:**
            *   Change subtitle to: "Your one-stop corner for all the up-to-date Arsenal transfer news".
            *   Remove the current logo.
        *   **Main Menu:**
            *   Simplify to two items: NEWS and ABOUT.
        *   **Hero Section:**
            *   Update widget labels to: Rumors, Official, Trending.
            *   Filter button remains non-functional for now.
        *   **Footer:**
            *   Remove the "TRUSTED SOURCES" column.
            *   Update "ALL FOR GOONERS" and "DISCLAIMER" sections with professional text.
    2.  **Develop a Centralized Sports API Client (`api/sports_api_client.py`):** Create a single module to handle all interactions with API-Football, Wikimedia, and SportMonks. Its first function will be `get_player_image()`.
    3.  **Implement API-Driven Image Standardization:** After the LLM identifies a player in an article, call the new API client to get a high-quality, professional headshot.
    4.  **Implement Automated Scraper Execution:** Set up a scheduled task to run the scraping script automatically every hour, ensuring the website is always up-to-date with the latest transfer news without manual intervention.
    5.  **Implement a Stable X/Twitter Scraping Solution:** Integrate a robust, reliable, and safer method for scraping tweets from key journalists, replacing the high-risk `twikit` implementation. This involves:
    *   **[COMPLETED] Local Nitter Instance Setup:** Successfully containerized Nitter and Redis using Docker Compose. Resolved critical configuration issues by creating a custom `entrypoint.sh` script that dynamically corrects the `nitter.conf` file at runtime, ensuring a stable connection to Redis. The local environment is now fully functional and ready for deployment.
    *   **[COMPLETED] Deployment on Northflank:** Successfully deployed the containerized Nitter application to Northflank. Resolved complex TLS proxy and file permission issues by creating a robust `Dockerfile` and a self-contained `entrypoint.sh` script that generates configurations at runtime, ensuring a stable and secure deployment.
    *   **[PENDING] Integration with Scraper:** Update the existing scraper to use the deployed Nitter instance's URL and implement robust error handling.
    *   **[PENDING] Testing and Validation:** Verify the end-to-end functionality of the deployed Nitter instance and its integration with the scraper, and monitor performance.

## Phase 2: Advanced Features

*   **Objective:** To enhance the value of our content by integrating official data and to build user engagement by introducing an interactive voting system.
*   **Key Initiatives:**
    1.  **Implement Search Functionality:** Implement a search bar to find articles by player name or keyword.
    2.  **Implement a Login-less Upvote System:**
        *   **What:** We will add a "thumb up" button to each news article.
        *   **How:** This will work without requiring user registration. We'll use the browser's `localStorage` to assign a unique anonymous ID to each visitor, preventing a single user from voting for the same article multiple times. A new `votes` table in Supabase will track these upvotes.
    3.  **Activate "Trending" Feature:** The "Trending" category in the hero section will now be powered by our new upvote system. Articles with the most community upvotes will be flagged as "Trending".
    4.  **Enrich News with Official Transfer Status:**
        *   **What:** Before the LLM summarizes an article, we will use our `SportsApiClient` to check API-Football for the official status of the transfer.
        *   **Why:** This allows us to add factual context (e.g., "This transfer is now confirmed") directly into the AI's prompt, resulting in more accurate and authoritative summaries. This turns our site from a rumor aggregator into a source of verified news.

---

**Phase 3: Automation & Feature Expansion**

*   **Objective:** To transition the pipeline into a fully automated, self-sufficient system and to expand the website's features beyond news into a broader football data hub.
*   **Key Initiatives:**
    1.  **Implement CI/CD and Scheduled Execution:** We will set up a GitHub Actions workflow to run our scraping script automatically on a schedule (e.g., every hour). This ensures the website is always up-to-date without any manual work.
    2.  **Develop New Frontend Data Modules:** We will build out the pages for the `LEAGUE TABLE` and `FIXTURES`, using our `SportsApiClient` to populate them with live data. This will make the site a much more valuable resource for fans.
    3.  **Future Feature: Push Notifications:** The architecture built in the previous phases will enable us to add a push notification system for breaking news as a future enhancement. 