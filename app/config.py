import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET = os.getenv("SECRET")
    TOKEN = os.getenv("TOKEN")

    # Control whether to allow downloading from generic/less popular sources
    IS_GENERIC_URL_OK = False

    # File size limits (in MB) - set to 0 to disable
    DOWNLOAD_VIDEO_SIZE_IN_MB = 20  # Max 20MB
    DOWNLOAD_VOICE_SIZE_IN_MB = 5
    DOWNLOAD_URL_SIZE_IN_MB = 40

    # Telegram API configurations
    BASE = "api.telegram.org"
    WEBHOOK_URL = ""  # Example: https://yourdomain.com/webhook
    WEBHOOK_PATH = ""  # Example: /webhook
    
    # Placeholder audio file for loading state
    LOADING_SONG = "https://s3.filebin.net/filebin/c08376ec0ac682f9575943f68e78dcf61f5a9c9d6b3bc9f9ccb3420a72a53f63/0f0217efbd0328b4c312f8bc31ffe13449d5f3bd401ed2533c3b56e7199b8f6f?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=7pMj6hGeoKewqmMQILjm%2F20250328%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250328T233625Z&X-Amz-Expires=60&X-Amz-SignedHeaders=host&response-cache-control=max-age%3D60&response-content-disposition=filename%3D%22clear-silent-track.mp3%22&response-content-type=audio%2Fmpeg&X-Amz-Signature=dbefa68d24d1295f89e235e9b79ac43ab0706f53540a7a88a3a800e2b7848446"
    
    # Path for storing session cookies (if needed)
    COOKIES_PATH = None
    
    # Telegram Admin User ID (for bot management)
    ADMIN = 8740947346  # Replace with actual admin ID

    # Load default bot response texts from JSON
    with open(os.path.join("app", "data", "default_texts.json")) as f:
        DEFAULT_TEXTS = json.load(f)

config = Config()
