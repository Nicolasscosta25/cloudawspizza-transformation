import time
import uuid


class PaymentError(Exception):
    pass


def process_payment(order: dict) -> dict:
    """Simulates a call to an external payment gateway.

    - Any item whose name contains "fail" (case-insensitive) makes the
      gateway reject the payment, raising PaymentError.
    - Any item whose name contains "slow" adds artificial latency, to make
      the synchronous blocking behavior demonstrable.
    """
    for item in order["items"]:
        name = item["name"].lower()
        if "slow" in name:
            time.sleep(3)
        if "fail" in name:
            raise PaymentError(f"payment gateway rejected item '{item['name']}'")

    time.sleep(0.2)  # baseline latency of a "real" gateway call

    return {
        "payment_id": str(uuid.uuid4()),
        "status": "approved",
        "amount": order["total"],
    }
