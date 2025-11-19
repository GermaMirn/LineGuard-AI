import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

import aio_pika
from aio_pika import ExchangeType, Message

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self) -> None:
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._updates_exchange: Optional[aio_pika.Exchange] = None

    async def connect(self, max_retries: int = 30, retry_delay: int = 10) -> None:
        if self._connection and not self._connection.is_closed:
            return

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка подключения к RabbitMQ ({attempt}/{max_retries})...")
                self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
                self._channel = await self._connection.channel()
                await self._channel.set_qos(prefetch_count=10)
                logger.info("✅ Успешно подключено к RabbitMQ")
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"❌ Не удалось подключиться к RabbitMQ после {max_retries} попыток: {e}")
                    raise
                logger.warning(f"⚠️ Ошибка подключения к RabbitMQ (попытка {attempt}/{max_retries}): {e}. Повтор через {retry_delay} сек...")
                await asyncio.sleep(retry_delay)

        await self._channel.declare_queue(
            settings.ANALYSIS_QUEUE_NAME,
            durable=True,
        )

        self._updates_exchange = await self._channel.declare_exchange(
            settings.ANALYSIS_UPDATES_EXCHANGE,
            ExchangeType.FANOUT,
            durable=True,
        )

    async def publish_task(self, payload: dict) -> None:
        if not self._channel:
            await self.connect()
        body = json.dumps(payload).encode("utf-8")
        message = Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        assert self._channel
        await self._channel.default_exchange.publish(
            message,
            routing_key=settings.ANALYSIS_QUEUE_NAME,
        )

    async def publish_update(self, payload: dict) -> None:
        if not self._channel or not self._updates_exchange:
            await self.connect()
        body = json.dumps(payload).encode("utf-8")
        message = Message(body, delivery_mode=aio_pika.DeliveryMode.NON_PERSISTENT)
        assert self._updates_exchange
        await self._updates_exchange.publish(message, routing_key="")

    async def consume_updates(
        self,
        handler: Callable[[dict], Awaitable[None]],
        queue_name: Optional[str] = None,
    ) -> None:
        if not self._channel or not self._updates_exchange:
            await self.connect()

        queue = await self._channel.declare_queue(
            queue_name or "",
            exclusive=queue_name is None,
            durable=False,
            auto_delete=True,
        )
        await queue.bind(self._updates_exchange)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(ignore_processed=True):
                    try:
                        payload = json.loads(message.body)
                    except json.JSONDecodeError:
                        continue
                    await handler(payload)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._updates_exchange = None


rabbitmq_client = RabbitMQClient()

