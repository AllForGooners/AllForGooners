import httpx
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SportsApiClient:
    """
    A centralized client to interact with various sports data APIs.
    This client will manage API keys and endpoints for services like
    API-Football, SportMonks, and Wikimedia.
    """
    def __init__(self):
        """
        Initializes the API client, loading necessary API keys from the environment.
        """
        self.apisports_key = os.getenv('APISPORTS_KEY')
        self.sportmonks_key = os.getenv('SPORTMONKS_API_KEY')
        
        self.apifootball_host = "v3.football.api-sports.io"
        self.apifootball_base_url = f"https://{self.apifootball_host}"
        
        if not self.apisports_key:
            print("Warning: API-Sports API key not found. Image retrieval may fail.")

        self.wikimedia_base_url = "https://en.wikipedia.org/w/api.php"
        # Add other base URLs as needed

    async def get_player_image(self, player_name: str) -> str | None:
        """
        Fetches a professional headshot for a given player using API-Football.

        Args:
            player_name: The full name of the player.

        Returns:
            The URL of the player's image, or None if not found.
        """
        if not self.apisports_key:
            print("API-Sports key not configured. Cannot fetch player image.")
            return None

        headers = {
            'x-apisports-key': self.apisports_key
        }
        params = {
            "search": player_name,
            "team": "42" # Arsenal's ID in API-Football
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.apifootball_base_url}/players",
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                data = response.json()

                if data.get("results", 0) > 0 and data["response"]:
                    player_photo_url = data["response"][0]["player"]["photo"]
                    print(f"Found image for {player_name}: {player_photo_url}")
                    return player_photo_url
                else:
                    print(f"No image found for {player_name} at API-Football.")
                    return None

            except httpx.HTTPStatusError as e:
                print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
                return None
            except httpx.RequestError as e:
                print(f"An error occurred while requesting {e.request.url!r}.")
                return None

async def main():
    """
    Main function for testing the SportsApiClient.
    """
    client = SportsApiClient()
    player_image_url = await client.get_player_image("Bukayo Saka")
    if player_image_url:
        print(f"Found image URL: {player_image_url}")
    else:
        print("Could not find an image for the player.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 