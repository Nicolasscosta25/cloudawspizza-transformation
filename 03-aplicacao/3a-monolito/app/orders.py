import json
import uuid
from typing import List

from pydantic import BaseModel

from app import db, payments


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
    payment_id: str


class OrderNotFound(Exception):
    pass


def _row_to_order(row: dict) -> Order:
    return Order(
        id=row["id"],
        customer_name=row["customer_name"],
        items=json.loads(row["items"]),
        total=float(row["total"]),
        status=row["status"],
        payment_id=row["payment_id"],
    )


def create_order(data: OrderCreate) -> Order:
    order_dict = data.model_dump()
    order_id = str(uuid.uuid4())

    # INTENTIONAL COUPLING (the whole point of this case study): payment
    # processing is called synchronously, inline, as part of order creation.
    # If it's slow, the order request is slow. If it raises, the order is
    # never written to the database. This is the monolith's tight coupling
    # the 3b microservices version exists to remove via async messaging.
    payment = payments.process_payment(order_dict)

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (id, customer_name, items, total, status, payment_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    order_id,
                    data.customer_name,
                    json.dumps([item.model_dump() for item in data.items]),
                    data.total,
                    "paid",
                    payment["payment_id"],
                ),
            )
    finally:
        conn.close()

    return Order(
        **data.model_dump(),
        id=order_id,
        status="paid",
        payment_id=payment["payment_id"],
    )


def list_orders() -> List[Order]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_order(row) for row in rows]


def get_order(order_id: str) -> Order:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise OrderNotFound(order_id)
    return _row_to_order(row)
