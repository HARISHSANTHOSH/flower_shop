import firebase_admin
from firebase_admin import credentials, messaging
import os
import json

_firebase_initialized = False

def initialize_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
        "universe_domain": "googleapis.com"
    })
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


def send_push_notification(fcm_token, title, body, data=None):
    """Send push notification to a specific device token"""
    try:
        initialize_firebase()
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        print(f"FCM Error: {e}")
        return None

def send_order_notification_to_all(order):
    from flowerapp.models import FCMToken
    tokens = list(FCMToken.objects.values_list('token', flat=True))
    for token in tokens:
        send_push_notification(
            fcm_token=token,
            title="🌸 New Order Received!",
            body=f"Order #{order.id} - ₹{order.total_amount} from {order.full_name}",
            data={"order_id": str(order.id), "type": "new_order"}
        )