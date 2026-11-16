from celery import shared_task
from django.conf import settings
from .models import Order
import boto3
import logging
import requests
from botocore.exceptions import ClientError
from .whatsapp import WhatsAppService, WhatsAppAPIError
import os
from asgiref.sync import async_to_sync
from django.db.models import F
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ADD THESE 2 FUNCTIONS TO YOUR tasks.py file
# ─────────────────────────────────────────────




def get_status_message(status):
    """Human-friendly message for each order status"""
    messages = {
        "payment_pending": "⏳ Waiting for payment...",
        "payment_failed":  "❌ Payment failed. Please retry.",
        "confirmed":       "✅ Order confirmed!",
        "processing":      "🔄 Your order is being prepared.",
        "shipped":         "🚚 Your plants are on the way!",
        "delivered":       "🌿 Delivered! Enjoy your plants.",
        "cancelled":       "❌ Order cancelled.",
        "refunded":        "💰 Refund initiated (5-7 business days).",
    }
    return messages.get(status, f"Status updated: {status}")


# ─────────────────────────────────────────────
# HOW TO USE THESE FUNCTIONS:
# ─────────────────────────────────────────────
#
# 1. When admin updates order status (in your views.py):
#    from .tasks import notify_customer_order_status
#    order.status = 'shipped'
#    order.save()
#    notify_customer_order_status(order)
#
# 2. When stock changes (in your views.py after order is placed):
#    from .tasks import notify_stock_update
#    flower.stock -= quantity
#    flower.save()
#    notify_stock_update(flower)
# ─────────────────────────────────────────────


@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    try:
        order = Order.objects.select_related("customer__user").get(id=order_id)
        user_email = order.customer.user.email
        if not user_email:
            return "No email found"

        send_email(
            to_email=user_email,
            subject=f"Order #{order.id} Confirmation",
            message=f"""Hi {order.customer.user.username},

Your order has been placed successfully!

Order ID: {order.id}
Total Amount: ₹{order.total_amount}
Status: {order.status}

Thank you for shopping with us 🌸
"""
        )
        return "Email sent successfully"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True, max_retries=3)
def send_order_cancellation_email(self, order_id):
    try:
        order = Order.objects.select_related("customer__user").get(id=order_id)
        customer = order.customer
        email = customer.user.email
        if not email:
            return "No email found"

        send_email(
            to_email=email,
            subject="Order Cancelled - Bloom Heaven",
            message=f"""Hi {customer.user.username},

Your order #{order.id} has been cancelled successfully.

{'A refund of ₹' + str(order.total_amount) + ' will be credited in 5-7 business days.'
 if order.payment_method == 'online' else ''}

Thank you for shopping with Bloom Heaven.
"""
        )
        return "Cancellation email sent"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True, max_retries=3)
def send_status_update_email(self, order_id, new_status):
    try:
        order = Order.objects.select_related("customer__user").get(id=order_id)
        user_email = order.customer.user.email
        if not user_email:
            return "No email found"

        if new_status == 'shipped':
            subject = f'Your Order #{order.id} is on the way! 🚚'
            message = f"""Hi {order.customer.user.username},

Great news! Your plants have been shipped and are on their way to you 🚚

Order ID: #{order.id}
Total Amount: ₹{order.total_amount}

Expected delivery: 1-2 business days.

For any queries call us at +91 88486 22015.

Thank you for shopping with Bloom Heaven 🌸
"""

        elif new_status == 'delivered':
            subject = f'Your Order #{order.id} has been Delivered! 🌿'
            message = f"""Hi {order.customer.user.username},

Your plants have arrived! We hope you love them 🌿

Order ID: #{order.id}
Total Amount: ₹{order.total_amount}

If you have any issues with your order, contact us within 24 hours:
📞 +91 88486 22015
📍 Thuravoor, Cherthala, Alappuzha

Thank you for shopping with Bloom Heaven 🌸
"""

        else:
            return f"No email needed for status: {new_status}"

        send_email(
            to_email=user_email,
            subject=subject,
            message=message
        )
        return f"Email sent for {new_status}"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


def get_ses_client():
    return boto3.client(
        'ses',
        region_name=os.getenv('AWS_REGION', 'ap-south-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )


def send_email(to_email, subject, message):
    client = get_ses_client()
    client.send_email(
        Source='hkc3392@gmail.com',
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': message}}
        }
    )



@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def send_whatsapp_order_notification(self, order_id):

    try:
        # Fetch the order from the database
        order = Order.objects.get(id=order_id)

        # Initialize WhatsApp service
        whatsapp = WhatsAppService()

        # Build order details
        message_components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(order.id)},
                    {"type": "text", "text": str(order.customer)},
                    {"type": "text", "text": str(order.total_amount)},
                ],
            }
        ]

        response = whatsapp.send_template_message(
            components=message_components
        )

        logger.info(
            "WhatsApp order notification accepted. Order ID: %s",
            order_id,
        )

        return response

    except Order.DoesNotExist:
        logger.error(
            "Order %s does not exist. WhatsApp notification cancelled.",
            order_id,
        )
        return None

    except WhatsAppAPIError as exc:

        if exc.retryable:
            raise self.retry(exc=exc)

        logger.exception(
            "Permanent WhatsApp API failure for order %s",
            order_id,
        )
        raise

    except (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    ) as exc:

        raise self.retry(exc=exc)

    except Exception:
        logger.exception(
            "Unexpected WhatsApp notification failure for order %s",
            order_id,
        )
        raise