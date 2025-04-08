import os
import telegram
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

async def send_photo_to_telegram(image_path, caption=""):
    """Sends a photo to the configured Telegram chat.

    Args:
        image_path (str): The full path to the image file.
        caption (str, optional): Optional caption for the photo. Defaults to "".

    Returns:
        tuple: (bool, str) indicating success and a message.
    """
    if not BOT_TOKEN or not CHAT_ID:
        return False, "Telegram Bot Token or Chat ID not configured in .env"
    if not os.path.exists(image_path):
        return False, f"Image file not found: {image_path}"

    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        print(f"Sending {os.path.basename(image_path)} to Telegram chat {CHAT_ID}...")
        with open(image_path, 'rb') as photo_file:
            await bot.send_photo(chat_id=CHAT_ID, photo=photo_file, caption=caption)
        print("Photo sent successfully.")
        return True, "Photo sent to Telegram."
    except telegram.error.TelegramError as e:
        error_msg = f"Telegram API Error: {e}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to send photo to Telegram: {e}"
        print(error_msg)
        return False, error_msg 