import httpx
import json
from datetime import datetime, timezone

# The prompt for the LLM
SYSTEM_PROMPT = """
You are an expert sports news editor for an Arsenal FC fan website.
You will be given a list of articles that are all related to Arsenal. Your PRIMARY and MOST IMPORTANT function is to identify which of them are about player transfers.

Your tasks are to:
1.  **Filter for Transfers**: First, EXAMINE all provided articles. DISCARD ANY article that is NOT STRICTLY about a player transfer or a major contract negotiation. General news, match results, or opinion pieces MUST be discarded. If no articles are about transfers, you MUST return an empty JSON array `[]`.

2.  **Group by Story**: After filtering, group the remaining transfer-only articles by the specific story they refer to (e.g., all articles about Arsenal's interest in a single player).

3.  **Synthesize and Summarize**: For each story group, you MUST write a single, comprehensive summary of ~150 words. This summary should **synthesize the key information from ALL articles in the group** to provide the most complete picture. Do not rely on just one source.

4.  **Select Primary Source URL**: After creating the summary, select the most credible source link from the group to serve as the primary URL. Prefer established news sites (BBC, Sky Sports) over social media or blog posts if available.

5.  **Image Selection**: CRITICALLY IMPORTANT - For each player, ensure the image_url is actually of the player mentioned in the headline. If an image doesn't match the player (e.g., shows a manager or logo instead), search for another image in the group that shows the correct player. If no good image exists, set image_url to null.

6.  **Standardize & Extract**: Create a standardized headline and pull out the player's name. Preserve the source name and URL from the **primary source you selected in step 4.**

Return the result ONLY as a valid JSON array of objects. Each object must represent a unique transfer story. The keys must be: 
"player_name", "headline", "news_summary", "url", "source_name", "image_url", "published_at".
"""

# A list of models to try in order of preference
LLM_MODELS = [
    "deepseek/deepseek-chat-v3-0324:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-4-maverick:free",
    "google/gemma-3-27b-it:free",
]

async def process_with_llm(articles, api_key):
    """
    Processes scraped articles with an LLM via OpenRouter to filter, deduplicate,
    and summarize, returning clean data ready for the database.
    It will try a list of models in order if one is rate-limited.
    """
    if not articles:
        return []

    processed_articles = []
    # Use an async HTTP client for performance
    async with httpx.AsyncClient() as client:
        for model in LLM_MODELS:
            print(f"Attempting to process with model: {model}...")
            try:
                response = await client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model, # Use the model from the list
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": json.dumps(articles)}
                        ]
                    },
                    timeout=180  # 3-minute timeout
                )
                response.raise_for_status()
                
                # If we get here, the request was successful
                print(f"Successfully processed with {model}.")
                
                # Extract the JSON content from the LLM's response
                llm_response_content = response.json()['choices'][0]['message']['content'].strip()
                
                # Clean the response: remove markdown fences if they exist
                if llm_response_content.startswith("```json"):
                    llm_response_content = llm_response_content[7:].strip()
                if llm_response_content.endswith("```"):
                    llm_response_content = llm_response_content[:-3].strip()

                # The LLM should return a JSON string, so we parse it
                processed_articles = json.loads(llm_response_content)

                # Add a timestamp to each article
                current_time = datetime.now(timezone.utc).isoformat()
                for article in processed_articles:
                    article['published_at'] = current_time

                return processed_articles # Success, exit the function

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(f"Model {model} is rate-limited. Trying next model...")
                    continue # Go to the next iteration of the loop
                else:
                    # For other HTTP errors, print and fail
                    print(f"LLM API Error: {e.response.status_code} - {e.response.text}")
                    return [] 
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Failed to parse LLM response from {model}: {e}")
                print(f"Raw response was: {llm_response_content}")
                continue # Try the next model, as this one might be giving bad output
            except Exception as e:
                print(f"An unexpected error occurred during LLM processing with {model}: {e}")
                return [] # Fail on unexpected errors
        
        # If the loop completes without a successful call
        print("All LLM models were rate-limited or failed. No articles processed.")
        return [] 