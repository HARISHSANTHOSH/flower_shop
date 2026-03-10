import json
from channels.generic.websocket import AsyncWebsocketConsumer


class OrderNotificationConsumer(AsyncWebsocketConsumer):
    """Existing: Notifies ADMIN of new orders"""

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated or not (user.is_superuser or user.is_staff):
            await self.close()
            return

        await self.channel_layer.group_add("admin_notifications", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("admin_notifications", self.channel_name)

    async def order_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class CustomerOrderConsumer(AsyncWebsocketConsumer):
    """NEW: Notifies CUSTOMER of their order status updates in real-time"""

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        # Each customer gets their own group: order_<order_id>
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.group_name = f"order_{self.order_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status_update(self, event):
        """Receives status update and sends to customer WebSocket"""
        await self.send(text_data=json.dumps(event["data"]))


class StockUpdateConsumer(AsyncWebsocketConsumer):
    """NEW: Broadcasts live stock updates to all customers viewing products"""

    async def connect(self):
        self.group_name = "stock_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def stock_update(self, event):
        """Receives stock update and sends to all connected customers"""
        await self.send(text_data=json.dumps(event["data"]))