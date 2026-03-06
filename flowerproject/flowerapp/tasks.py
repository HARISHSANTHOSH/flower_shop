from celery import shared_task
from django.conf import settings
from .models import Order
import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")


@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    try:
        order = Order.objects.select_related("customer__user").get(id=order_id)
        user_email = order.customer.user.email
        if not user_email:
            return "No email found"

        resend.Emails.send({
            "from": "Bloom Heaven <onboarding@resend.dev>",
            "to": [user_email],
            "subject": f"Order #{order.id} Confirmation",
            "text": f"""Hi {order.customer.user.username},

Your order has been placed successfully!

Order ID: {order.id}
Total Amount: ₹{order.total_amount}
Status: {order.status}

Thank you for shopping with us 🌸
"""
        })
        return "Email sent successfully"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True, max_retries=3)
def send_order_cancellation_email(self, order_id):
    try:
        order    = Order.objects.select_related("customer__user").get(id=order_id)
        customer = order.customer
        email    = customer.user.email
        if not email:
            return "No email found"

        resend.Emails.send({
            "from": "Bloom Heaven <onboarding@resend.dev>",
            "to": [email],
            "subject": "Order Cancelled - Bloom Heaven",
            "text": f"""Hi {customer.user.username},

Your order #{order.id} has been cancelled successfully.

{'A refund of ₹' + str(order.total_amount) + ' will be credited in 5-7 business days.'
 if order.payment_method == 'online' else ''}

Thank you for shopping with Bloom Heaven.
"""
        })
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

        resend.Emails.send({
            "from": "Bloom Heaven <onboarding@resend.dev>",
            "to": [user_email],
            "subject": subject,
            "text": message,
        })
        return f"Email sent for {new_status}"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)