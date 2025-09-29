import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Literal, Generator, Coroutine, Any

from aiohttp import ClientSession
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class MediaItem(BaseModel):
    type: Literal["photo", "video"]
    media: str


class Photo(MediaItem):
    type: Literal["photo"] = "photo"

    def __init__(self, file_id: str):
        super().__init__(media=file_id, type="photo")


class Video(MediaItem):
    type: Literal["video"] = "video"

    def __init__(self, file_id: str):
        super().__init__(media=file_id, type="video")


class TelegramSender:
    _url_template: str = "https://api.telegram.org/bot{token}/{method}"

    def __init__(
        self,
        token: str,
        batch_size: int = 25,
        delay_between_batches: float = 1.1,
        use_mongo: bool = True,
        mongo_uri: str = "mongodb://localhost:27017",
        mongo_db: str = "telegram_sender",
        parse_mode: Literal["MarkdownV2", "Markdown", "HTML"] = "HTML",
    ):
        self._token: str = token
        self._batch_size: int = batch_size
        self._delay_between_batches: float = delay_between_batches
        self._use_mongo: bool = use_mongo
        self._mongo_uri: str = mongo_uri
        self._mongo_db: str = mongo_db
        self._parse_mode: str = parse_mode
        self._mongo_collection: AsyncIOMotorCollection | None = None
        self._method: Literal["sendMessage", "sendPhoto", "sendVideo", "sendMediaGroup"] = "sendMessage"
        self._url: str = ""

        self._rate_limited_messages: list[dict] = []
        self._global_retry_after: float = 0.0

    async def run(
        self,
        chat_ids: list[int],
        text: str = "",
        media_items: list[MediaItem] | None = None,
        reply_markup: dict | None = None,
        disable_web_page_preview: bool = False
    ) -> tuple[int, int]:
        """Runs the sending process and returns (delivered, not_delivered)."""
        if media_items is None:
            media_items = []

        if len(media_items) > 1:
            self._method = "sendMediaGroup"
        elif len(media_items) == 1:
            if media_items[0].type == "photo":
                self._method = "sendPhoto"
            elif media_items[0].type == "video":
                self._method = "sendVideo"
        else:
            self._method = "sendMessage"

        self._url = self._url_template.format(token=self._token, method=self._method)
        data = self._prepare_data(text, media_items, reply_markup, disable_web_page_preview)

        async with ClientSession() as self._session:
            if self._use_mongo:
                from motor.motor_asyncio import AsyncIOMotorClient

                client: AsyncIOMotorClient = AsyncIOMotorClient(self._mongo_uri)
                collection_name = self._get_collection_name()
                self._mongo_collection = client[self._mongo_db][collection_name]
            return await self._send_messages(data, chat_ids)

    def _prepare_data(
        self,
        text: str,
        media_items: list[MediaItem],
        reply_markup: dict | None,
        disable_web_page_preview: bool,
    ) -> dict[str, Any]:
        """Prepares data for sending based on the method."""
        if self._method == "sendMediaGroup":
            media_group = []
            for index, item in enumerate(media_items):
                media_dict = item.dict()
                if index == 0:
                    media_dict["caption"] = text
                    media_dict["parse_mode"] = self._parse_mode
                media_group.append(media_dict)
            data: dict[str, Any] = {"media": json.dumps(media_group)}
            if reply_markup:
                logger.warning("reply_markup is not supported in sendMediaGroup")
        elif self._method == "sendPhoto":
            data = {
                "photo": media_items[0].media,
                "caption": text,
                "parse_mode": self._parse_mode,
            }
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
        elif self._method == "sendVideo":
            data = {
                "video": media_items[0].media,
                "caption": text,
                "parse_mode": self._parse_mode,
            }
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
        else:  # sendMessage
            data = {
                "text": text,
                "parse_mode": self._parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            }
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
        return data

    def _get_collection_name(self) -> str:
        """Generates a unique MongoDB collection name using Moscow time."""
        moscow_time = time.gmtime(time.time() + 3 * 60 * 60)
        return time.strftime("%d_%m_%Y__%H_%M_%S", moscow_time)

    async def _send_messages(self, data: dict, chat_ids: list[int]) -> tuple[int, int]:
        """Creates batches and executes them."""
        batches = self._create_send_batches(data, chat_ids)
        return await self._execute_batches(batches)

    def _create_send_batches(self, data: dict, chat_ids: list[int]) -> Generator[list, None, None]:
        """Yields batches of _send_message coroutines."""
        batch = []
        for chat_id in chat_ids:
            data_with_id = data.copy()
            data_with_id["chat_id"] = chat_id
            batch.append(self._send_message(data_with_id))
            if len(batch) >= self._batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def _send_message(self, data: dict) -> tuple[bool, bool]:
        """
        Sends one message. Returns (is_success, is_429).
        If is_429=True, the message is added to _rate_limited_messages.
        """
        try:
            async with self._session.post(self._url, data=data) as response:
                response_json = await response.json()

            if self._use_mongo and self._mongo_collection is not None:
                await self._mongo_collection.insert_one(response_json)

            if response.status != 200:
                error_code = response_json.get("error_code")
                if error_code == 429:
                    retry_after = response_json.get("parameters", {}).get("retry_after", 0)
                    logger.error(f"429 for chat_id={data['chat_id']}, retry_after={retry_after}")
                    self._rate_limited_messages.append(data)
                    self._global_retry_after = max(self._global_retry_after, retry_after)
                    return False, True
                else:
                    logger.error(f"Failed for {data['chat_id']}: {response_json}")
                return False, False
            else:
                logger.info(f"Delivered to {data['chat_id']}")
                return True, False
        except Exception as e:
            logger.exception(f"Exception for {data['chat_id']}: {e}")
            return False, False

    async def _process_batch_messages(self, batch: list[Coroutine[Any, Any, tuple[bool, bool]]]) -> tuple[int, int]:
        """Processes a batch with as_completed. Returns (delivered, non_429_failures)."""
        delivered, non_429_failures = 0, 0
        for future in asyncio.as_completed(batch):
            is_success, is_429 = await future
            if is_success:
                delivered += 1
            else:
                if not is_429:
                    non_429_failures += 1
        return delivered, non_429_failures

    async def _resend_rate_limited_messages(self) -> tuple[int, int]:
        """
        Retries the messages in _rate_limited_messages once.
        Returns (delivered, not_delivered_for_these).
        """
        if not self._rate_limited_messages:
            return 0, 0

        logger.info(f"Re-sending {len(self._rate_limited_messages)} rate-limited messages")
        msgs_to_retry = self._rate_limited_messages.copy()
        self._rate_limited_messages.clear()

        futures = [self._send_message(d) for d in msgs_to_retry]
        delivered, non_429_failures = await self._process_batch_messages(futures)

        second_429_count = len(self._rate_limited_messages)
        not_delivered = non_429_failures + second_429_count
        self._rate_limited_messages.clear()
        return delivered, not_delivered

    async def _execute_batches(self, batches: Generator[list, None, None]) -> tuple[int, int]:
        """
        Executes batches, handles 429 with a pause, and returns (delivered, not_delivered).
        """
        total_delivered, total_not_delivered = 0, 0
        sleep_time = 0.0

        for batch_index, batch in enumerate(batches, start=1):
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            batch_start_time = time.monotonic()

            d, nd = await self._process_batch_messages(batch)
            total_delivered += d
            total_not_delivered += nd

            if self._global_retry_after > 0:
                logger.info(f"Pausing {self._global_retry_after}s due to 429 in batch #{batch_index}")
                await asyncio.sleep(self._global_retry_after)
                self._global_retry_after = 0.0

                d2, nd2 = await self._resend_rate_limited_messages()
                total_delivered += d2
                total_not_delivered += nd2

            sleep_time = max(batch_start_time + self._delay_between_batches - time.monotonic(), 0.0)
        return total_delivered, total_not_delivered
