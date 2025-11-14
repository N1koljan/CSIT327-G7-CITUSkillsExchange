# core/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if the user is authenticated
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.group_name = f'user_{self.user.id}_notifications'

            # Join user-specific group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            # Reject the connection if the user is not authenticated
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group if user was authenticated
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # This method is called when we send a message to the group
    async def send_notification(self, event):
        message = event['message']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': message
        }))