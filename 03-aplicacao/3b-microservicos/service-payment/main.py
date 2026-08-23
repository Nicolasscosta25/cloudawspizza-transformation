import json
import logging
import os
import random
import threading
import time

import pika
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-payment")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "order_created"

app = FastAPI(title="CloudAWSPizza - service-payment")

_consumer_ready = False


def _connect(max_retries: int = 10, delay_seconds: float = 3.0):
    """Connects to RabbitMQ, retrying a few times before giving up.

    Same rationale as service-order: docker-compose starts every service
    concurrently, so RabbitMQ may not be reachable yet when this container
    boots. Retrying avoids a crash-loop while the broker finishes starting.
    """
    for attempt in range(1, max_retries + 1):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=30)
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            logger.info("Connected to RabbitMQ at %s (attempt %d)", RABBITMQ_HOST, attempt)
            return connection, channel
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("RabbitMQ not ready (attempt %d/%d): %s", attempt, max_retries, exc)
            time.sleep(delay_seconds)
    logger.error(
        "Could not connect to RabbitMQ after %d attempts; consumer will keep retrying",
        max_retries,
    )
    return None, None


def _process_payment(order: dict) -> None:
    """Simulates a call to an external payment gateway.

    Random latency stands in for network/processing time, and a random
    failure simulates the gateway rejecting a payment. The failure is only
    logged — it must never crash the consumer thread, otherwise one bad
    order would stop payment processing for every order after it.
    """
    time.sleep(random.uniform(0.2, 1.5))
    if random.random() < 0.1:
        logger.error("Payment FAILED for order %s (simulated gateway error)", order.get("id"))
        return
    logger.info("Payment APPROVED for order %s (total=%s)", order.get("id"), order.get("total"))


def _on_message(channel, method, properties, body):
    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Discarding malformed message: %s", body)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        _process_payment(order)
    except Exception:
        logger.exception("Unexpected error processing order %s", order.get("id"))
    finally:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def _consume_loop():
    global _consumer_ready
    while True:
        connection, channel = _connect()
        if channel is None:
            time.sleep(5)
            continue
        try:
            _consumer_ready = True
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message)
            logger.info("Waiting for order_created events...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("Lost connection to RabbitMQ: %s. Reconnecting...", exc)
        finally:
            _consumer_ready = False
            try:
                connection.close()
            except Exception:
                pass
            time.sleep(3)


@app.on_event("startup")
def startup():
    # The consumer runs in a background thread so this same process can
    # also serve /health over HTTP for docker-compose healthchecks.
    thread = threading.Thread(target=_consume_loop, daemon=True)
    thread.start()


@app.get("/health")
def health():
    return {"status": "ok", "consumer_connected": _consumer_ready}
