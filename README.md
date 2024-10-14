# telegram_sender: Asynchronous Telegram Message Sender

**telegram_sender** is an asynchronous Python package designed to send messages, photos, and videos (single or multiple, in any order) to multiple Telegram users efficiently. It leverages Python's `asyncio` and `aiohttp` libraries to handle concurrent HTTP requests, making it suitable for broadcasting messages to a large number of users with optimal performance.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [How It Works](#how-it-works)
- [Advantages](#advantages)
- [Usage Examples](#usage-examples)
  - [Example 1 - Simple Text Message Broadcast](#example-1---simple-text-message-broadcast)
  - [Example 2 - Sending a Single Photo with Text and Buttons](#example-2---sending-a-single-photo-with-text-and-buttons)
  - [Example 3 - Sending Multiple Photos and Videos in Any Order](#example-3---sending-multiple-photos-and-videos-in-any-order)
  - [Example 4 - Sending a Single Video with Text and Buttons](#example-4---sending-a-single-video-with-text-and-buttons)
  - [Example 5 - Logging Messages in MongoDB](#example-5---logging-messages-in-mongodb)
- [Getting Started](#getting-started)
- [How to Obtain Media File IDs](#how-to-obtain-media-file-ids)

## Overview

In modern applications, especially those involving notifications or updates, sending messages to a multitude of users is a common requirement. **telegram_sender** addresses this need by providing an asynchronous solution that sends messages in batches, handles errors gracefully, and optionally logs the results to MongoDB for record-keeping or analysis.

## Installation

You can install **telegram_sender** directly from PyPI:

```bash
pip install telegram_sender
```

Make sure you have Python 3.10 or higher installed.

## How It Works

**telegram_sender** operates by:

1. **Preparing Message Data**: It formats the message content, including text, photos, and videos (single or multiple, in any order), and optional reply markups, in a way that is compatible with the Telegram Bot API. You can also specify the `parse_mode` (e.g., `HTML`, `Markdown`) when initializing the class to control how text is parsed by Telegram.

2. **Batching Requests**: To avoid exceeding Telegram's rate limits and to improve performance, it divides the list of recipient chat IDs into batches. Each batch contains a specified number of messages (`batch_size`).

3. **Asynchronous Sending**: Using asynchronous HTTP requests, it sends each batch concurrently, ensuring that the program doesn't block while waiting for responses.

4. **Delay Between Batches**: After sending a batch, it waits for a specified delay (`delay_between_batches`) before sending the next one. This delay helps comply with Telegram's rate limits and prevents server overload.

5. **Error Handling**: If a message fails to send, the error is logged using Python's `logging` module. The process continues with the next messages without interruption.

6. **MongoDB Logging (Optional)**: If enabled, the results of each message send operation are stored in a MongoDB collection. This feature is useful for auditing, analytics, or retry mechanisms.

## Advantages

- **Asynchronous Processing**: Utilizes `asyncio` and `aiohttp` for non-blocking operations, making it efficient for high-volume message sending.
- **Batch Management**: Sends messages in configurable batches to optimize performance and comply with rate limits.
- **Error Resilience**: Continues sending messages even if some fail, and logs errors for later review.
- **Configurable**: Offers flexibility through parameters such as batch size, delay intervals, parse mode, and MongoDB settings.
- **Optional Logging**: Allows enabling or disabling MongoDB logging based on your needs.

## Usage Examples

### Example 1 - Simple Text Message Broadcast

This example demonstrates how to send a simple text message to multiple users.

```python
import asyncio
from telegram_sender import TelegramSender

async def main():
    # Initialize the message sender
    sender = TelegramSender(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        batch_size=30,  # Increased batch size to 30 messages concurrently
        delay_between_batches=1.5,  # 1.5-second delay between batches
        use_mongo=False,  # No MongoDB logging
        parse_mode="Markdown"  # Setting parse_mode to Markdown
    )

    # Message text
    text = "*Hello!* This is a test message."

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

### Example 2 - Sending a Single Photo with Text and Buttons

This example shows how to send a single photo with a caption and inline buttons.

```python
import asyncio
from telegram_sender import TelegramSender, Photo

async def main():
    # Initialize the message sender
    sender = TelegramSender(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        batch_size=20,  # Send 20 messages concurrently
        delay_between_batches=2.0,  # 2-second delay between batches
        use_mongo=True,  # Log results in MongoDB
        parse_mode="HTML"  # Using HTML as parse_mode
    )

    # Prepare the data
    text = "Check out this <b>beautiful</b> photo!"
    media_items = [
        Photo("PHOTO_FILE_ID")  # Single photo
    ]
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Like", "callback_data": "like"},
             {"text": "Dislike", "callback_data": "dislike"}]
        ]
    }

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids, media_items=media_items, reply_markup=reply_markup)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

### Example 3 - Sending Multiple Photos and Videos in Any Order

This example demonstrates how to send multiple photos and videos in a single message using `sendMediaGroup`, preserving the order of media items.

```python
import asyncio
from telegram_sender import TelegramSender, Photo, Video

async def main():
    # Initialize the message sender
    sender = TelegramSender(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        batch_size=2,  # Send 2 messages concurrently
        delay_between_batches=1.5,  # 1.5-second delay between batches
        use_mongo=False  # No MongoDB logging
    )

    # Prepare the data
    text = "Here are some highlights from our latest event!"
    media_items = [
        Photo("PHOTO_FILE_ID_1"),
        Video("VIDEO_FILE_ID_1"),
        Photo("PHOTO_FILE_ID_2"),
    ]

    # Note: reply_markup is not supported with sendMediaGroup
    reply_markup = None

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids, media_items=media_items)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

**Important Notes:**

- When sending multiple media files using `sendMediaGroup`, the `reply_markup` parameter (e.g., inline keyboards) is **not supported** by the Telegram API. If you need to include buttons, consider sending them in a separate message after the media group.
- The `media_items` list allows you to mix photos and videos in any order. Each item is an instance of `Photo` or `Video`.

### Example 4 - Sending a Single Video with Text and Buttons

This example shows how to send a single video with a caption and inline buttons.

```python
import asyncio
from telegram_sender import TelegramSender, Video

async def main():
    # Initialize the message sender
    sender = TelegramSender(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        batch_size=10,  # Send 10 messages concurrently
        delay_between_batches=1.0,  # 1-second delay between batches
        use_mongo=False,  # No MongoDB logging
        parse_mode="Markdown"  # Using Markdown as parse_mode
    )

    # Prepare the data
    text = "*Watch* this exciting video!"
    media_items = [
        Video("VIDEO_FILE_ID")  # Single video
    ]
    reply_markup = {
        "inline_keyboard": [
            [{"text": "👍 Like", "callback_data": "like"},
             {"text": "👎 Dislike", "callback_data": "dislike"}]
        ]
    }

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids, media_items=media_items, reply_markup=reply_markup)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

### Example 5 - Logging Messages in MongoDB

This example demonstrates how to enable MongoDB logging to keep records of sent messages.

```python
import asyncio
from telegram_sender import TelegramSender

async def main():
    # Initialize the message sender with MongoDB logging
    sender = TelegramSender(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        batch_size=10,  # Batch size of 10 messages
        delay_between_batches=1.0,  # 1-second delay between batches
        use_mongo=True,  # Enable MongoDB logging
        mongo_uri="mongodb://localhost:27017",  # MongoDB URI
        mongo_db="telegram_logs"  # Database name
    )

    # Message text
    text = "This message will be logged in MongoDB."

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

## Getting Started

To start using **telegram_sender**, you need:

- **Python 3.10+**: The codebase uses modern Python features and type annotations.
- **Telegram Bot Token**: Obtain one by creating a bot through [BotFather](https://telegram.me/botfather) on Telegram.
- **Install the Package**: Install **telegram_sender** using pip:

  ```bash
  pip install telegram_sender
  ```

- **MongoDB Instance (Optional)**: If you wish to enable logging, have access to a MongoDB database.

## How to Obtain Media File IDs

To reuse photos or videos in Telegram without re-uploading, you can obtain their `file_id` by sending the media as a message through your bot to any user (e.g., yourself or any user who has interacted with the bot).

Here's a simple function to get a photo or video `file_id`:

```python
import requests

def get_media_token(bot_token: str, media_path: str, chat_id: int, media_type: str = "photo") -> str:
    with open(media_path, "rb") as media_file:
        response = requests.post(
            url=f"https://api.telegram.org/bot{bot_token}/send{media_type.capitalize()}",
            files={media_type: media_file},
            data={"chat_id": chat_id}
        )
        response_data = response.json()
        if not response_data.get("ok"):
            raise Exception(f"Error sending media: {response_data}")
        result = response_data["result"]
        media_key = "photo" if media_type == "photo" else "video"
        media = result[media_key]
        if isinstance(media, list):
            return media[-1]["file_id"]
        else:
            return media["file_id"]

# Example usage:
# Replace "YOUR_TELEGRAM_BOT_TOKEN" with your bot token and use your own chat_id or any user who interacted with the bot.
# photo_token = get_media_token("YOUR_TELEGRAM_BOT_TOKEN", "/path/to/photo.jpg", YOUR_CHAT_ID, media_type="photo")
# video_token = get_media_token("YOUR_TELEGRAM_BOT_TOKEN", "/path/to/video.mp4", YOUR_CHAT_ID, media_type="video")
```
