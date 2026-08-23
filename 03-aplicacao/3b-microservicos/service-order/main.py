import json
import logging
import os
import time
import uuid
from typing import List, Optional

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-order")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "order_created"

app = FastAPI(title="CloudAWSPizza - service-order")


class OrderItem(BaseModel):
    name: str
    quantity: int = 1


class OrderCreate(BaseModel):
    customer_name: str
    items: List[OrderItem]
    total: float


class Order(OrderCreate):
    id: str
    status: str


_orders: dict[str, Order] = {}
_connection: Optional[pika.BlockingConnection] = None


def _connect(max_retries: int = 10, delay_seconds: float = 3.0) -> Optional[pika.BlockingConnection]:
    """Connects to RabbitMQ, retrying a few times before giving up.

    docker-compose starts every service concurrently, so RabbitMQ's TCP
    port may not be accepting connections yet when this service boots.
    Retrying here avoids crash-looping the container while the broker
    finishes starting.
    """
    for attempt in range(1, max_retries + 1):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=30)
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            logger.info("Connected to RabbitMQ at %s (attempt %d)", RABBITMQ_HOST, attempt)
            return connection
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("RabbitMQ not ready (attempt %d/%d): %s", attempt, max_retries, exc)
            time.sleep(delay_seconds)
    logger.error(
        "Could not connect to RabbitMQ after %d attempts; will keep retrying lazily on publish",
        max_retries,
    )
    return None


@app.on_event("startup")
def startup():
    global _connection
    _connection = _connect()


def _publish(order: Order) -> None:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = _connect(max_retries=3, delay_seconds=1.0)
    if _connection is None:
        logger.error(
            "RabbitMQ unavailable; order %s was created but the order_created "
            "event could not be published",
            order.id,
        )
        return
    try:
        channel = _connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(order.model_dump()),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info("Published order_created event for order %s", order.id)
    except pika.exceptions.AMQPError as exc:
        logger.error("Failed to publish order_created event for order %s: %s", order.id, exc)
        _connection = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders", response_model=Order, status_code=201)
def create_order(data: OrderCreate):
    order = Order(**data.model_dump(), id=str(uuid.uuid4()), status="pending_payment")
    _orders[order.id] = order

    # Publish the event and return immediately, without waiting for
    # service-payment to process anything. This is the intentional
    # decoupling this phase exists to demonstrate: in the 3a monolith,
    # payment was called synchronously inline with order creation, so a
    # stuck/down payment path took the order down with it. Here, order
    # creation only depends on the message broker accepting the event —
    # if service-payment is down for a few minutes, orders keep being
    # accepted normally and get processed once it comes back.
    _publish(order)

    return order


@app.get("/orders", response_model=List[Order])
def list_orders():
    return list(_orders.values())


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    order = _orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order
