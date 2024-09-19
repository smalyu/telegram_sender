# SenderMessages: Asynchronous Telegram Message Sender

**SenderMessages** is an asynchronous Python class designed to send messages and photos to multiple Telegram users efficiently. It leverages Python's `asyncio` and `aiohttp` libraries to handle concurrent HTTP requests, making it suitable for broadcasting messages to a large number of users with optimal performance.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Advantages](#advantages)
- [Usage Examples](#usage-examples)
- [Getting Started](#getting-started)

## Overview

In modern applications, especially those involving notifications or updates, sending messages to a multitude of users is a common requirement. **SenderMessages** addresses this need by providing an asynchronous solution that sends messages in batches, handles errors gracefully, and optionally logs the results to MongoDB for record-keeping or analysis.

## How It Works

**SenderMessages** operates by:

1. **Preparing Message Data**: It formats the message content, including text, photos, and optional reply markups, in a way that is compatible with the Telegram Bot API.

2. **Batching Requests**: To avoid exceeding Telegram's rate limits and to improve performance, it divides the list of recipient chat IDs into batches (packs). Each batch contains a specified number of messages (`batch_size`).

3. **Asynchronous Sending**: Using asynchronous HTTP requests, it sends each batch concurrently, ensuring that the program doesn't block while waiting for responses.

4. **Delay Between Batches**: After sending a batch, it waits for a specified delay (`delay_between_batches`) before sending the next one. This delay helps comply with Telegram's rate limits and prevents server overload.

5. **Error Handling**: If a message fails to send, the error is logged using Python's `logging` module. The process continues with the next messages without interruption.

6. **MongoDB Logging (Optional)**: If enabled, the results of each message send operation are stored in a MongoDB collection. This feature is useful for auditing, analytics, or retry mechanisms.

## Advantages

- **Asynchronous Processing**: Utilizes `asyncio` and `aiohttp` for non-blocking operations, making it efficient for high-volume message sending.

- **Batch Management**: Sends messages in configurable batches to optimize performance and comply with rate limits.

- **Error Resilience**: Continues sending messages even if some fail, and logs errors for later review.

- **Configurable**: Offers flexibility through parameters such as batch size, delay intervals, and MongoDB settings.

- **Optional Logging**: Allows enabling or disabling MongoDB logging based on your needs.

## Usage Examples

### Example 1: Simple Text Message Broadcast

This example demonstrates how to send a simple text message to multiple users.

```python
import asyncio

async def main():
    # Initialize the message sender
    sender = SenderMessages(
        token='YOUR_TELEGRAM_BOT_TOKEN',
        batch_size=5,  # Send 5 messages concurrently
        delay_between_batches=1.5,  # 1.5-second delay between batches
        use_mongo=False  # No MongoDB logging
    )

    # Message text
    text = "Hello! This is a test message."

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

### Example 2: Sending a Photo with Text and Buttons

This example shows how to send a photo with a caption and inline buttons.

```python
import asyncio

async def main():
    # Initialize the message sender
    sender = SenderMessages(
        token='YOUR_TELEGRAM_BOT_TOKEN',
        batch_size=3,  # Send 3 messages concurrently
        delay_between_batches=2.0,  # 2-second delay between batches
        use_mongo=True  # Log results in MongoDB
    )

    # Prepare the data
    text = "Check out this beautiful photo!"
    photo_token = "PHOTO_FILE_ID"  # Telegram file ID of the photo
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Like", "callback_data": "like"},
             {"text": "Dislike", "callback_data": "dislike"}]
        ]
    }

    # List of chat IDs
    chat_ids = [123456789, 987654321, 456123789]

    # Start the message sending process
    delivered, not_delivered = await sender.run(text, chat_ids, photo_token=photo_token, reply_markup=reply_markup)

    # Output statistics
    print(f"Successfully sent: {delivered}, Failed to send: {not_delivered}")

# Run the asynchronous task
asyncio.run(main())
```

### Example 3: Logging Messages in MongoDB

This example demonstrates how to enable MongoDB logging to keep records of sent messages.

```python
import asyncio

async def main():
    # Initialize the message sender with MongoDB logging
    sender = SenderMessages(
        token='YOUR_TELEGRAM_BOT_TOKEN',
        batch_size=10,  # Batch size of 10 messages
        delay_between_batches=1.0,  # 1-second delay between batches
        use_mongo=True,  # Enable MongoDB logging
        mongo_uri='mongodb://localhost:27017',  # MongoDB URI
        mongo_db='telegram_logs'  # Database name
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

To start using **SenderMessages**, you need:

- **Python 3.10+**: The codebase uses modern Python features and type annotations.
- **Telegram Bot Token**: Obtain one by creating a bot through [BotFather](https://telegram.me/botfather) on Telegram.
- **Install Requirements**: The necessary dependencies are listed in the `requirements.txt` file. Install them with:
  ```bash
  pip install -r requirements.txt
  ```
- **MongoDB Instance (Optional)**: If you wish to enable logging, have access to a MongoDB database.
