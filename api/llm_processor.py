import httpx
import json
from datetime import datetime, timezone

# The prompt for the LLM
SYSTEM_PROMPT = """
You are an expert sports news editor for an Arsenal FC fan website. 
Your tasks are to:
1.  **Deduplicate**: Group articles about the same transfer story.
2.  **Filter**: Discard any news not strictly about player transfers or major contract negotiations (e.g., ignore match results, general club news).
3.  **Summarize**: For each valid transfer story, write an engaging summary of ~150 words.
4.  **Extract Data**: Pull out the player's name, a final headline, the source URL, the source name, and the main image URL from the article's content.

Return the result ONLY as a valid JSON array of objects. Each object must have these keys: 
"player_name", "headline", "news_summary", "url", "source_name", "image_url", "published_at".
"""

async def process_with_llm(articles, api_key):
    """
    Processes scraped articles with an LLM via OpenRouter to filter, deduplicate,
    and summarize, returning clean data ready for the database.
    """
    if not articles:
        return []

    processed_articles = []
    # Use an async HTTP client for performance
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-pro",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(articles)}
                    ]
                },
                timeout=300  # 5-minute timeout for a potentially long response
            )
            response.raise_for_status()
            
            # Extract the JSON content from the LLM's response
            llm_response_content = response.json()['choices'][0]['message']['content']
            
            # The LLM should return a JSON string, so we parse it
            processed_articles = json.loads(llm_response_content)

            # Add a timestamp to each article
            current_time = datetime.now(timezone.utc).isoformat()
            for article in processed_articles:
                article['published_at'] = current_time

            return processed_articles

        except httpx.HTTPStatusError as e:
            print(f"LLM API Error: {e.response.status_code} - {e.response.text}")
            return [] # Return empty list on failure
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Raw response was: {llm_response_content}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred during LLM processing: {e}")
            return [] 