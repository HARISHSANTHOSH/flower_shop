from django.urls import re_path
from flowerapp import consumers

websocket_urlpatterns = [
    # Existing: Admin notifications
    re_path(r"ws/notifications/$", consumers.OrderNotificationConsumer.as_asgi()),

    # NEW: Customer order status updates → ws/orders/42/
    re_path(r"ws/orders/(?P<order_id>\d+)/$", consumers.CustomerOrderConsumer.as_asgi()),

    # NEW: Live stock updates → ws/stock/
    re_path(r"ws/stock/$", consumers.StockUpdateConsumer.as_asgi()),
]