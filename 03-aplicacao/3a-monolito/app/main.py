from fastapi import FastAPI, HTTPException

from app import orders
from app.orders import Order, OrderCreate
from app.payments import PaymentError

app = FastAPI(title="CloudAWSPizza - Monolito")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders", response_model=Order, status_code=201)
def create_order(data: OrderCreate):
    try:
        return orders.create_order(data)
    except PaymentError as exc:
        raise HTTPException(status_code=502, detail=f"payment failed: {exc}")


@app.get("/orders", response_model=list[Order])
def list_orders():
    return orders.list_orders()


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    try:
        return orders.get_order(order_id)
    except orders.OrderNotFound:
        raise HTTPException(status_code=404, detail="order not found")
