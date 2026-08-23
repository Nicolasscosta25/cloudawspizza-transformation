import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Simula o envio de uma notificacao (email/SMS/push) quando um novo pedido
    e criado na CloudAWSPizza. Em producao, este handler seria invocado por um
    evento (SNS, EventBridge ou SQS) publicado pelo service-order."""
    order_id = event.get("order_id", "desconhecido")
    customer = event.get("customer", "cliente")

    message = f"Pedido {order_id} recebido para {customer}. Notificacao enviada."
    logger.info(message)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": message}),
    }
