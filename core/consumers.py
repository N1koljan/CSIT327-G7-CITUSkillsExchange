# core/consumers.py

import json
from .utils import get_conversation_id
from .models import CustomUser
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.utils import timezone


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


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    Tasks: 6.1.4 (Configure WebSockets), 6.1.5 (Save chat history), 6.1.8 (Unread messages)
    """

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # 👇 CHANGED: Get conversation_id directly from URL (not username)
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']

        # WebSocket group name
        self.room_group_name = f"chat_{self.conversation_id}"

        # Join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 👇 Send chat history immediately on connect
        history = await self.get_chat_history()

        await self.send(text_data=json.dumps({
            "type": "chat_history",
            "messages": [
                {
                    "id": msg["id"],
                    "sender_id": msg["sender_id"],
                    "recipient_id": msg["recipient_id"],
                    "sender_username": await self.get_username(msg["sender_id"]),
                    "content": msg["content"],
                    "timestamp": msg["created_at"].isoformat(),
                    "is_read": msg["is_read"]
                }
                for msg in history
            ]
        }))

    async def disconnect(self, close_code):
        """Called when the WebSocket closes."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat messages. (Task 6.1.5: Save chat history)"""
        content = data.get('message', '').strip()
        recipient_username = data.get('recipient')

        # Validate message
        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Empty message not allowed'
            }))
            return

        if not recipient_username:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Recipient not specified'
            }))
            return

        # Save message to database
        message = await self.save_message(
            sender=self.user,
            recipient_username=recipient_username,
            content=content,
            conversation_id=self.conversation_id
        )

        if message:
            # Broadcast message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': content,
                    'sender': self.user.username,
                    'sender_id': self.user.id,
                    'recipient': recipient_username,
                    'timestamp': message.created_at.isoformat(),
                    'message_id': message.id,
                }
            )

    async def handle_typing(self, data):
        """Handle typing indicator. (Task 6.1.7)"""
        is_typing = data.get('is_typing', False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_read_receipt(self, data):
        """Handle message read receipts. (Task 6.1.8: Unread messages)"""
        message_id = data.get('message_id')

        if message_id:
            success = await self.mark_message_as_read(message_id)

            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_receipt',
                        'message_id': message_id,
                        'read_by': self.user.username,
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'recipient': event['recipient'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator back to the sender
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'read_by': event['read_by'],
        }))

    # Database operations
    @database_sync_to_async
    def save_message(self, sender, recipient_username, content, conversation_id):
        """Save message to database and return with sender username."""
        try:
            from .models import CustomUser, Message
            recipient = CustomUser.objects.get(username=recipient_username)

            message = Message.objects.create(
                sender=sender,
                recipient=recipient,
                content=content,
                conversation_id=conversation_id,
                created_at=timezone.now(),
                is_read=False
            )
            return message
        except CustomUser.DoesNotExist:
            print(f"Recipient {recipient_username} not found")
            return None
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read. (Task 6.1.8: Add unread message)"""
        try:
            from .models import Message
            message = Message.objects.get(id=message_id, recipient=self.user)
            message.is_read = True
            message.save(update_fields=['is_read'])
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            print(f"Error marking message as read: {e}")
            return False

    @database_sync_to_async
    def get_chat_history(self):
        from .models import Message

        return list(
            Message.objects.filter(conversation_id=self.conversation_id)
            .order_by("created_at")
            .values("id", "sender_id", "recipient_id", "content", "created_at", "is_read")
        )

    @database_sync_to_async
    def get_username(self, user_id):
        """Get username from user_id"""
        try:
            from .models import CustomUser
            user = CustomUser.objects.get(id=user_id)
            return user.username
        except CustomUser.DoesNotExist:
            return "Unknown"