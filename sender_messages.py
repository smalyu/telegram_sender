import asyncio
import json
import logging
import time
from typing import Literal

from aiohttp import ClientSession
from motor import motor_asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SenderMessages:
    _url_template: str = 'https://api.telegram.org/bot{token}/{method}'

    def __init__(
        self,
        token: str,
        batch_size: int = 25,
        delay_between_batches: float = 1.1,
        use_mongo: bool = True,
        mongo_uri: str = 'mongodb://localhost:27017',
        mongo_db: str = 'tg-bot-sender',
        parse_mode: str = 'HTML'
    ):
        self._token = token
        self._batch_size = batch_size
        self._delay_between_batches = delay_between_batches
        self._use_mongo = use_mongo
        self._mongo_uri = mongo_uri
        self._mongo_db = mongo_db
        self._parse_mode = parse_mode
        self._mongo_collection = None
        self._method: Literal["sendMessage", "sendPhoto", "sendMediaGroup"] | None = None
        self._url = None

    async def run(
        self,
        text: str,
        chat_ids: list[int],
        photo_tokens: list[str] | None = None,
        reply_markup: dict | None = None,
    ) -> (int, int):
        """Starts the message sending process."""
        if photo_tokens and len(photo_tokens) > 1:
            self._method = 'sendMediaGroup'
        elif photo_tokens and len(photo_tokens) == 1:
            self._method = 'sendPhoto'
        else:
            self._method = 'sendMessage'

        self._url = self._url_template.format(token=self._token, method=self._method)
        data = self._prepare_data(text, photo_tokens, reply_markup)
        if self._use_mongo:
            collection_name = self._get_collection_name()
            self._mongo_collection = motor_asyncio.AsyncIOMotorClient(self._mongo_uri)[self._mongo_db][collection_name]
        return await self._send_messages(data, chat_ids)

    def _prepare_data(self, text: str, photo_tokens: list[str] | None, reply_markup: dict | None) -> dict:
        """Prepares data for sending based on the method."""
        if self._method == 'sendMediaGroup':
            media = []
            for i, photo_token in enumerate(photo_tokens):
                item = {'type': 'photo', 'media': photo_token}
                if i == 0:
                    item['caption'] = text
                    item['parse_mode'] = self._parse_mode
                media.append(item)
            data = {'media': json.dumps(media)}
            if reply_markup:
                logger.warning("reply_markup is not supported in sendMediaGroup")
        elif self._method == 'sendPhoto':
            data = {'photo': photo_tokens[0], 'caption': text, 'parse_mode': self._parse_mode}
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
        else:  # sendMessage
            data = {'text': text, 'parse_mode': self._parse_mode}
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
        return data

    def _get_collection_name(self) -> str:
        """Creates a unique name for the MongoDB collection using Moscow time."""
        moscow_time = time.gmtime(time.time() + 3 * 60 * 60)
        return time.strftime('%d_%m_%Y__%H_%M_%S', moscow_time)

    async def _send_messages(self, data: dict, chat_ids: list[int]) -> (int, int):
        """Starts the message sending process with logging."""
        async with ClientSession() as session:
            batches = self._create_send_batches(data, chat_ids, session)
            return await self._execute_batches(batches)

    def _create_send_batches(self, data: dict, chat_ids: list[int], session: ClientSession) -> list[list]:
        """Creates batches of send message coroutines."""
        batches = []
        current_batch = []

        for chat_id in chat_ids:
            data_with_id = data.copy()
            data_with_id['chat_id'] = chat_id
            current_batch.append(self._send_message(data_with_id, session))
            if len(current_batch) >= self._batch_size:
                batches.append(current_batch)
                current_batch = []
        if current_batch:
            batches.append(current_batch)
        return batches

    async def _send_message(self, data: dict, session: ClientSession) -> bool:
        """Sends a single message and logs the result to MongoDB if enabled."""
        try:
            async with session.post(self._url, data=data) as response:
                response_json = await response.json()

            if self._use_mongo and self._mongo_collection is not None:
                await self._mongo_collection.insert_one(response_json)

            if response.status != 200:
                logger.error(f"Failed to send message to {data['chat_id']}: {response_json}")
                return False
            else:
                logger.info(f"Message to {data['chat_id']} delivered")
                return True
        except Exception as e:
            logger.exception(f"Exception occurred while sending message to {data['chat_id']}: {e}")
            return False

    async def _execute_batches(self, batches: list[list]) -> (int, int):
        """Processes the batches of send message coroutines."""
        delivered, not_delivered = 0, 0

        for batch in batches:
            batch_start_time = time.monotonic()

            results = await asyncio.gather(*batch, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception) or not result:
                    not_delivered += 1
                else:
                    delivered += 1

            time_elapsed = time.monotonic() - batch_start_time
            if time_elapsed < self._delay_between_batches:
                await asyncio.sleep(self._delay_between_batches - time_elapsed)

        return delivered, not_delivered
