import httpx
import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import re
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class SportsApiClient:
    """
    A centralized client to interact with various sports data APIs.
    This client manages API keys and endpoints for services like
    API-Football, TheSportsDB, SportMonks, and Wikipedia.
    """
    def __init__(self):
        """
        Initializes the API client, loading necessary API keys from the environment.
        """
        self.apifootball_key = os.getenv('API_FOOTBALL_API_KEY')
        self.sportmonks_key = os.getenv('SPORTMONKS_API_KEY')
        self.thesportsdb_key = os.getenv('THESPORTSDB_API_KEY')  # Add TheSportsDB API key (free tier doesn't need key)
        self.wikimedia_client_id = os.getenv('WIKIMEDIA_CLIENT_ID')
        self.wikimedia_client_secret = os.getenv('WIKIMEDIA_CLIENT_SECRET')
        self.wikipedia_access_token = os.getenv('WIKIPEDIA_ACCESS_TOKEN')
        self.user_agent = os.getenv('USER_AGENT', 'AllForGooners/1.0')
        
        # API base URLs
        self.apifootball_host = "v3.football.api-sports.io"
        self.apifootball_base_url = f"https://{self.apifootball_host}"
        self.sportmonks_base_url = "https://api.sportmonks.com/v3/football"
        self.thesportsdb_base_url = "https://www.thesportsdb.com/api/v1/json/3"  # Free tier URL
        self.wikimedia_base_url = "https://en.wikipedia.org/w/api.php"
        
        # Create local directory for downloaded images if it doesn't exist
        self.images_dir = Path("frontend/images/players")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.apifootball_key:
            print("Warning: API-Football API key not found. Image retrieval may fail.")

    async def _get_current_season(self, league_id: int = 39) -> str:
        """
        Fetches the current season for a given league.
        
        For free plan users, returns "2023" as per API limitations.

        Args:
            league_id: The ID of the league (default is 39 for Premier League).

        Returns:
            The current season year as a string, or a default if not found.
        """
        if not self.apifootball_key:
            print("API-Football key not configured. Cannot fetch current season.")
            return "2023"  # Fallback for free plan (supported season)

        # Check if using free plan
        print("Using season 2023 for free plan users (API limitation)")
        return "2023"  # Use 2023 for free plan users

    async def get_player_image(self, player_name: str, team_id: int) -> str | None:
        """
        Fetches a professional headshot for a given player using multiple APIs.
        Tries API-Football first, then SportMonks, then TheSportsDB, and finally Wikipedia.

        Args:
            player_name: The full name of the player.
            team_id: The API-Football ID of the team.

        Returns:
            The URL of the player's image, or None if not found.
        """
        # Normalize the player name
        player_name = player_name.strip()
        
        # Try API-Football first
        image_url = await self._get_image_from_api_football(player_name, team_id)
        if image_url:
            return image_url
            
        # Then try SportMonks
        image_url = await self._get_image_from_sportmonks(player_name)
        if image_url:
            return image_url
            
        # Then try TheSportsDB
        image_url = await self._get_image_from_thesportsdb(player_name)
        if image_url:
            return image_url
            
        # Finally try Wikipedia as fallback
        image_url = await self._get_image_from_wikipedia(player_name)
        if image_url:
            return image_url
            
        return None

    async def _get_image_from_api_football(self, player_name: str, team_id: int) -> str | None:
        """
        Attempts to fetch a player image from API-Football.
        
        Args:
            player_name: The player's name to search for.
            team_id: The team ID in API-Football's system.
            
        Returns:
            The URL of the player's image, or None if not found.
        """
        if not self.apifootball_key:
            return None
            
        print(f"Trying API-Football for '{player_name}'...")
        
        current_season = await self._get_current_season()
        
        headers = {
            'x-apisports-key': self.apifootball_key
        }
        params = {
            "search": player_name,
            "team": str(team_id),
            "season": current_season
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.apifootball_base_url}/players",
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("results", 0) > 0 and data["response"]:
                    player_photo_url = data["response"][0]["player"]["photo"]
                    print(f"Found image for {player_name}: {player_photo_url}")
                    return player_photo_url
                else:
                    print(f"No image found for {player_name} at API-Football.")
                    print(f"API Response: {data}")
                    return None

            except httpx.HTTPStatusError as e:
                print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
                return None
            except httpx.RequestError as e:
                print(f"Error requesting {e.request.url!r}.")
                return None

    async def _get_image_from_thesportsdb(self, player_name: str) -> str | None:
        """
        Attempts to fetch a player image from TheSportsDB.
        
        Args:
            player_name: The player's name to search for.
            
        Returns:
            The URL of the player's image, or None if not found.
        """
        print(f"Trying TheSportsDB for '{player_name}'...")
        
        # Format the player name for the API
        # TheSportsDB search works better with spaces replaced by underscores
        formatted_name = player_name.replace(" ", "_")
        
        async with httpx.AsyncClient() as client:
            try:
                # Search for the player
                response = await client.get(
                    f"{self.thesportsdb_base_url}/searchplayers.php",
                    params={"p": formatted_name},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Check if players were found
                if data.get("player") and len(data["player"]) > 0:
                    # Look for Arsenal players specifically
                    arsenal_players = [p for p in data["player"] 
                                      if p.get("strTeam") == "Arsenal" 
                                      or "Arsenal" in p.get("strTeam", "")]
                    
                    # Use Arsenal player if found, otherwise use the first result
                    player = arsenal_players[0] if arsenal_players else data["player"][0]
                    
                    # Get the player image - TheSportsDB offers multiple image types
                    image_url = player.get("strCutout")  # Cutout has transparent background
                    if not image_url:
                        image_url = player.get("strThumb")  # Regular thumbnail
                    if not image_url:
                        image_url = player.get("strRender")  # Full body render
                    
                    if image_url:
                        print(f"Found image for {player_name} at TheSportsDB: {image_url}")
                        return image_url
                    else:
                        print(f"No image found for {player_name} at TheSportsDB.")
                        return None
                else:
                    print(f"No player data found for {player_name} at TheSportsDB.")
                    return None
                    
            except httpx.HTTPStatusError as e:
                print(f"TheSportsDB error response {e.response.status_code} while requesting {e.request.url!r}.")
                return None
            except httpx.RequestError as e:
                print(f"Error requesting {e.request.url!r} from TheSportsDB.")
                return None
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"Error parsing TheSportsDB response: {e}")
                return None

    async def _get_image_from_sportmonks(self, player_name: str) -> str | None:
        """
        Attempts to fetch a player image from SportMonks.
        
        Args:
            player_name: The player's name to search for.
            
        Returns:
            The URL of the player's image, or None if not found.
        """
        if not self.sportmonks_key:
            return None
            
        print(f"Trying SportMonks for '{player_name}'...")
        
        # SportMonks v3 API parameters
        params = {
            "api_token": self.sportmonks_key
        }
            
        async with httpx.AsyncClient() as client:
            try:
                # The search query must be part of the URL path, not a query parameter.
                response = await client.get(
                    f"{self.sportmonks_base_url}/players/search/{player_name}",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("data") and len(data["data"]) > 0:
                    player = data["data"][0]
                    
                    # Look for the image in the included media
                    if "media" in player and len(player["media"]) > 0:
                        for media_item in player["media"]:
                            if media_item.get("type") == "image":
                                image_url = media_item.get("url")
                                if image_url:
                                    print(f"Found image for {player_name} at SportMonks: {image_url}")
                                    return image_url
                    
                    print(f"No image found in media data for {player_name} at SportMonks.")
                    return None
                else:
                    print(f"No player data found for {player_name} at SportMonks.")
                    return None
                    
            except httpx.HTTPStatusError as e:
                print(f"SportMonks error response {e.response.status_code} while requesting {e.request.url!r}.")
                return None
            except httpx.RequestError as e:
                print(f"Error requesting {e.request.url!r} from SportMonks.")
                return None

    async def _get_image_from_wikipedia(self, player_name: str) -> str | None:
        """
        Fetches an image from Wikipedia for the given player.
        
        Args:
            player_name: The name of the player to search for.
            
        Returns:
            The URL of the player's image, or None if not found.
        """
        print(f"Trying Wikipedia for '{player_name}'...")
        headers = {'User-Agent': self.user_agent}
        
        # First, find the Wikipedia page for the player
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{player_name} footballer Arsenal",  # Adding "footballer Arsenal" improves results
            "utf8": 1,
            "formatversion": 2
        }
        
        async with httpx.AsyncClient() as client:
            try:
                search_response = await client.get(
                    self.wikimedia_base_url,
                    params=search_params,
                    headers=headers,
                    timeout=10.0
                )
                search_response.raise_for_status()
                search_data = search_response.json()
                
                if not search_data.get("query", {}).get("search"):
                    print(f"No Wikipedia page found for {player_name}.")
                    return None
                    
                # Get the page title of the first search result
                page_title = search_data["query"]["search"][0]["title"]
                
                # Now get the images from this page
                image_params = {
                    "action": "query",
                    "format": "json",
                    "titles": page_title,
                    "prop": "images",
                    "imlimit": 50,  # Get up to 50 images
                    "formatversion": 2
                }
                
                image_response = await client.get(
                    self.wikimedia_base_url,
                    params=image_params,
                    headers=headers,
                    timeout=10.0
                )
                image_response.raise_for_status()
                image_data = image_response.json()
                
                # Extract image names, filter out SVG and low quality images
                image_names = []
                if image_data.get("query", {}).get("pages"):
                    page = image_data["query"]["pages"][0]
                    if page.get("images"):
                        for image in page["images"]:
                            img_name = image.get("title", "")
                            # Skip SVG, PNG diagrams, and small icons
                            if (img_name.endswith(".jpg") or img_name.endswith(".jpeg")) and \
                               not any(x in img_name.lower() for x in ["logo", "icon", "badge", "kit", "flag"]):
                                image_names.append(img_name)
                
                if not image_names:
                    print(f"No suitable images found for {player_name} on Wikipedia.")
                    return None
                
                # Get URL for the first suitable image
                img_name = image_names[0].replace("File:", "")
                img_params = {
                    "action": "query",
                    "format": "json",
                    "titles": f"File:{img_name}",
                    "prop": "imageinfo",
                    "iiprop": "url|size",
                    "iiurlwidth": 500,  # Request a 500px width version
                    "formatversion": 2
                }
                
                img_response = await client.get(
                    self.wikimedia_base_url,
                    params=img_params,
                    headers=headers,
                    timeout=10.0
                )
                img_response.raise_for_status()
                img_data = img_response.json()
                
                if img_data.get("query", {}).get("pages"):
                    page = img_data["query"]["pages"][0]
                    if page.get("imageinfo"):
                        image_url = page["imageinfo"][0].get("thumburl")
                        if image_url:
                            print(f"Found image from Wikipedia: {image_url}")
                            return image_url
                
                print(f"No image URL found for {player_name} on Wikipedia.")
                return None
                
            except httpx.HTTPStatusError as e:
                print(f"Wikipedia error response {e.response.status_code} while requesting {e.request.url!r}.")
                return None
            except httpx.RequestError as e:
                print(f"Error requesting {e.request.url!r} from Wikipedia.")
                return None
            except (KeyError, IndexError) as e:
                print(f"Error parsing Wikipedia response: {e}")
                return None

    async def download_player_image(self, player_name: str, image_url: str) -> str | None:
        """
        Downloads a player image to the local filesystem.
        
        Args:
            player_name: Name of the player for file naming.
            image_url: URL of the image to download.
            
        Returns:
            Local path to the saved image, or None if download failed.
        """
        if not image_url:
            return None
            
        # Clean the player name for filename
        clean_name = re.sub(r'[^\w\s-]', '', player_name).strip().replace(' ', '_')
        file_extension = os.path.splitext(image_url)[1]
        if not file_extension:
            file_extension = '.jpg'  # Default to jpg if extension not found
            
        # Ensure extension starts with a dot
        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension
            
        # Create the file path
        file_path = self.images_dir / f"{clean_name}{file_extension}"
        
        try:
            # Download the image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                
                # Save to disk
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                print(f"Image saved to {file_path}")
                return str(file_path)
                
        except httpx.HTTPStatusError as e:
            print(f"Error downloading image: {e.response.status_code} for URL {image_url}")
            return None
        except httpx.RequestError as e:
            print(f"Error requesting image: {e} for URL {image_url}")
            return None
        except Exception as e:
            print(f"Error saving image: {e}")
            return None


async def test_player_image(client: SportsApiClient, player_name: str) -> bool:
    """
    Tests image retrieval for a single player.
    
    Args:
        client: The SportsApiClient instance.
        player_name: The name of the player to find an image for.
        
    Returns:
        True if an image was found, False otherwise.
    """
    print(f"\nTesting with {player_name}:")
    player_image_url = await client.get_player_image(player_name, 42)
    if player_image_url:
        local_path = await client.download_player_image(player_name, player_image_url)
        if local_path:
            print(f"✓ Found and saved image for '{player_name}'")
            return True
        else:
            print(f"✗ Found image URL but failed to download for '{player_name}'")
            return False
    else:
        print(f"✗ Could not find any image for '{player_name}' from any source.")
        return False


async def main():
    """
    Main function for testing the SportsApiClient.
    """
    client = SportsApiClient()
    
    # Test with multiple Arsenal players
    players = ["Bukayo Saka", "Martin Odegaard", "Declan Rice"]
    results = {}
    
    for player in players:
        results[player] = await test_player_image(client, player)
    
    # Print summary
    print("\n--- Results Summary ---")
    for player, found in results.items():
        status = "✓ Found" if found else "✗ Not found"
        print(f"{player} image: {status}")


if __name__ == "__main__":
    asyncio.run(main()) 