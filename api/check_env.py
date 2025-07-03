import os
from dotenv import load_dotenv

print("=== Environment Variables Diagnostic ===")

# Try to find .env file in both current directory and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

print(f"Script directory: {script_dir}")
print(f"Root directory: {root_dir}")

print(f".env exists in script dir: {os.path.exists(os.path.join(script_dir, '.env'))}")
print(f".env exists in root dir: {os.path.exists(os.path.join(root_dir, '.env'))}")

# Try loading from root directory
dotenv_path = os.path.join(root_dir, '.env')
print(f"Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# Check Twitter credentials
twitter_username = os.getenv("TWITTER_USERNAME")
twitter_email = os.getenv("TWITTER_EMAIL")
twitter_password = os.getenv("TWITTER_PASSWORD")

print(f"TWITTER_USERNAME loaded: {twitter_username is not None} {'(' + twitter_username + ')' if twitter_username else ''}")
print(f"TWITTER_EMAIL loaded: {twitter_email is not None} {'(' + twitter_email[:4] + '...)' if twitter_email else ''}")
print(f"TWITTER_PASSWORD loaded: {twitter_password is not None} {'(****)' if twitter_password else ''}")

# Check if quotes might be affecting the variables
if twitter_username and (twitter_username.startswith('"') or twitter_username.startswith("'")):
    print("NOTE: TWITTER_USERNAME has quotes that might need to be stripped")

# Check other important variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
openrouter_key = os.getenv("OPENROUTER_API_KEY")

print(f"SUPABASE_URL loaded: {supabase_url is not None}")
print(f"SUPABASE_SERVICE_KEY loaded: {supabase_key is not None}")
print(f"OPENROUTER_API_KEY loaded: {openrouter_key is not None}")

# Try importing the Twitter client to check for potential library issues
try:
    from twikit import Client
    print("Twikit library imported successfully")
except ImportError as e:
    print(f"Error importing Twikit: {e}")

print("=== Diagnostic Complete ===") 