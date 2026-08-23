import uuid
from typing import List

from pydantic import BaseModel

from app import payments


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


_orders: dict[str, Order] = {}


class OrderNotFound(Exception):
    pass


def create_order(data: OrderCreate) -> Order:
    order_dict = data.model_dump()
    order_dict["id"] = str(uuid.uuid4())

    # INTENTIONAL COUPLING (the whole point of this case study): payment
    # processing is called synchronously, inline, as part of order creation.
    # If it's slow, the order request is slow. If it raises, the order is
    # never created. This is the monolith's tight coupling the 3b
    # microservices version exists to remove via async messaging.
    payment = payments.process_payment(order_dict)

    order = Order(
        **data.model_dump(),
        id=order_dict["id"],
        status="paid",
        payment_id=payment["payment_id"],
    )
    _orders[order.id] = order
    return order


def list_orders() -> List[Order]:
    return list(_orders.values())


def get_order(order_id: str) -> Order:
    try:
        return _orders[order_id]
    except KeyError:
        raise OrderNotFound(order_id)
