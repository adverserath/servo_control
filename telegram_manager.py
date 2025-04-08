import os
import time
import requests
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TelegramManager:
    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        # Check if Telegram integration is properly configured
        self.is_configured = (self.bot_token is not None and self.chat_id is not None)
        
        if not self.is_configured:
            print("Warning: Telegram integration not configured. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env file")
        else:
            print(f"Telegram integration configured for chat ID: {self.chat_id}")
    
    def send_photo(self, photo_path):
        """
        Send a photo to the configured Telegram chat
        
        Args:
            photo_path (str): Path to the photo file to send
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_configured:
            print("Error: Telegram integration not configured")
            return False
        
        if not os.path.exists(photo_path):
            print(f"Error: Photo file not found at {photo_path}")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {'chat_id': self.chat_id}
                
                response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                print(f"Photo successfully sent to Telegram chat {self.chat_id}")
                return True
            else:
                print(f"Failed to send photo to Telegram. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending photo to Telegram: {e}")
            return False
    
    def send_photo_async(self, photo_path):
        """
        Send a photo asynchronously in a background thread
        
        Args:
            photo_path (str): Path to the photo file to send
        """
        thread = threading.Thread(target=self.send_photo, args=(photo_path,), daemon=True)
        thread.start()
        return thread 