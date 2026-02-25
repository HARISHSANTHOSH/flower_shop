from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order





@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    try:
        order = Order.objects.select_related("customer__user").get(id=order_id)

        user_email = order.customer.user.email
        if not user_email:
            return "No email found"

        subject = f"Order #{order.id} Confirmation"
        message = f"""
Hi {order.customer.user.username},

Your order has been placed successfully!

Order ID: {order.id}
Total Amount: ₹{order.total_amount}
Status: {order.status}

Thank you for shopping with us 🌸
"""

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )

        return "Email sent successfully"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task
def send_order_cancellation_email(order_id):
    order    = Order.objects.get(id=order_id)
    customer = order.customer
    email    = customer.user.email

    subject = 'Order Cancelled - Bloom Haven'
    message = f'''
    Hi {customer.user.username},

    Your order #{order.id} has been cancelled successfully.

    {'A refund of ₹' + str(order.total_amount) + ' will be credited in 5-7 business days.' 
     if order.payment_method == 'online' else ''}

    Thank you for shopping with Bloom Haven.
    '''

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])