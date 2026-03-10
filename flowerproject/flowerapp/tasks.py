from celery import shared_task
from django.conf import settings
from .models import Order
import boto3
from botocore.exceptions import ClientError
import os
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .firebase import send_push_notification


# ─────────────────────────────────────────────
# ADD THESE 2 FUNCTIONS TO YOUR tasks.py file
# ─────────────────────────────────────────────

def notify_customer_order_status(order):
    """
    Send real-time WebSocket notification to CUSTOMER when their order status changes.
    Call this whenever you update order.status
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"order_{order.id}",
        {
            "type": "order_status_update",
            "data": {
                "type": "status_update",
                "order_id": order.id,
                "status": order.status,
                "message": get_status_message(order.status),
            }
        }
    )


def notify_stock_update(flower):
    """
    Broadcast live stock update to ALL customers.
    Call this whenever Flower.stock changes (after save).
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "stock_updates",
        {
            "type": "stock_update",
            "data": {
                "type": "stock_update",
                "flower_id": flower.id,
                "flower_name": flower.name,
                "stock": flower.stock,
                # Frontend shows "Only X left!" when stock <= 5
                "low_stock": flower.stock <= 5,
            }
        }
    )


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


def notify_admin_new_order(order):
    """Send real-time WebSocket notification to superadmin"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "admin_notifications",
        {
            "type": "order_notification",
            "data": {
                "type": "new_order",
                "order_id": order.id,
                "customer": order.customer.user.username,
                "total": str(order.total_amount),
                "status": order.status,
                "payment_method": order.payment_method,
                "message": f"New order #{order.id} from {order.customer.user.username} - ₹{order.total_amount}",
            }
        }
    )