import os
import asyncio
from dotenv import load_dotenv
from twikit import Client

async def test_login():
    print("=== Testing Twitter Login ===")
    
    # Use absolute path to .env file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    dotenv_path = os.path.join(root_dir, '.env')
    print(f"Loading environment from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
    
    # Get credentials and strip quotes if present
    username = os.getenv("TWITTER_USERNAME")
    email = os.getenv("TWITTER_EMAIL")
    password = os.getenv("TWITTER_PASSWORD")
    
    # Check if credentials exist
    if not username or not email or not password:
        print("Error: Missing Twitter credentials in .env file")
        return
    
    if username.startswith('"') and username.endswith('"') or username.startswith("'") and username.endswith("'"):
        username = username[1:-1]
        print("Stripped quotes from username")
    
    if email.startswith('"') and email.endswith('"') or email.startswith("'") and email.endswith("'"):
        email = email[1:-1]
        print("Stripped quotes from email")
    
    if password.startswith('"') and password.endswith('"') or password.startswith("'") and password.endswith("'"):
        password = password[1:-1]
        print("Stripped quotes from password")
    
    print(f"Username: {username}")
    print(f"Email: {email[:4]}...")
    print(f"Password: {'*' * len(password)}")
    
    try:
        print("Initializing Twitter client...")
        client = Client('en-US')
        
        print("Attempting to login...")
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )
        print("Login successful! Saving cookies...")
        client.save_cookies('cookies.json')
        print("Cookies saved to cookies.json")
    except Exception as e:
        print(f"Login failed with error: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_login()) 