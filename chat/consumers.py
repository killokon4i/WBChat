import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Conversation,
    Message,
    MessageStatus,
    TypingIndicator,
    OnlineStatus,
    UserConversation,
)

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat messaging.
    Handles: sending/receiving messages, typing indicators, read receipts
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Reject anonymous users
        if not self.user.is_authenticated:
            print("Rejected: user not authenticated")
            await self.close()
            return

        # Verify user is part of conversation
        is_member = await self.check_conversation_membership()
        if not is_member:
            print("Rejected: user not in conversation")
            await self.close()
            return

        self._room_group_joined = False
        if self.channel_layer:
            try:
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name,
                )
                self._room_group_joined = True
            except Exception as exc:
                print('WS group_add failed:', exc)

        await self.accept()
        print("WebSocket connected successfully")
        await self.update_online_status(online=True)
        await self.broadcast_presence_safe()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if getattr(self, '_room_group_joined', False) and self.channel_layer:
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name,
                )
            except Exception as exc:
                print('WS group_discard failed:', exc)

        await self.update_online_status(online=False)
        await self.clear_typing_indicator()
        await self.broadcast_presence_safe()

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'edit_message':
                await self.handle_edit_message(data)
            elif message_type == 'delete_message':
                await self.handle_delete_message(data)
            elif message_type == 'pin_message':
                await self.handle_pin_message(data)
            elif message_type == 'reaction':
                await self.handle_reaction(data)
            elif message_type == 'heartbeat':
                await self.touch_online_activity()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        content = data.get('message', '')
        reply_to_id = data.get('reply_to')

        if not content.strip():
            return

        # Save message to database
        message = await self.create_message(content, reply_to_id)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': await self.message_to_dict(message),
            }
        )

        # Create message statuses for all participants
        await self.create_message_statuses(message)
        await self.broadcast_inbox_update(message.id)

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)

        if is_typing:
            await self.set_typing_indicator()
        else:
            await self.clear_typing_indicator()

        # Broadcast typing status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt for messages"""
        message_ids = data.get('message_ids', [])
        await self.mark_messages_as_read(message_ids)

        # Notify others about read receipts
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'user_id': self.user.id,
                'message_ids': message_ids,
            }
        )

    async def handle_edit_message(self, data):
        """Handle message editing"""
        message_id = data.get('message_id')
        new_content = data.get('content', '')

        if not new_content.strip():
            return

        message = await self.edit_message(message_id, new_content)
        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message': await self.message_to_dict(message),
                }
            )

    async def handle_delete_message(self, data):
        """Handle message deletion"""
        message_id = data.get('message_id')
        
        success = await self.delete_message(message_id)
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'user_id': self.user.id,
                }
            )

    async def handle_reaction(self, data):
        """Handle message reactions"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        action = data.get('action', 'add')  # 'add' or 'remove'

        if action == 'add':
            await self.add_reaction(message_id, emoji)
        else:
            await self.remove_reaction(message_id, emoji)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'user_id': self.user.id,
                'emoji': emoji,
                'action': action,
            }
        )

    # WebSocket message handlers (called by group_send)
    async def chat_message(self, event):
        """Send chat message to WebSocket (client deduplicates by message id)."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send own typing indicator back
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user_id': event['user_id'],
            'message_ids': event['message_ids'],
        }))

    async def message_edited(self, event):
        """Send edited message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message'],
        }))

    async def message_deleted(self, event):
        """Send message deletion notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
        }))

    async def message_reaction(self, event):
        """Send reaction update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'emoji': event['emoji'],
            'action': event['action'],
        }))

    async def user_join(self, event):
        """Notify about user joining"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_join',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def user_leave(self, event):
        """Notify about user leaving"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_leave',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    # Database operations
    @database_sync_to_async
    def broadcast_inbox_update(self, message_id):
        from chat.realtime import notify_chat_message_by_id
        notify_chat_message_by_id(message_id, self.user.id)

    @database_sync_to_async
    def check_conversation_membership(self):
        """Check if user is a member of the conversation"""
        return UserConversation.objects.filter(
            user=self.user,
            conversation_id=self.conversation_id,
            left_at__isnull=True
        ).exists()

    @database_sync_to_async
    def create_message(self, content, reply_to_id=None):
        """Create a new message in the database"""
        message = Message.objects.create(
            conversation_id=self.conversation_id,
            author=self.user,
            content=content,
            reply_to_id=reply_to_id,
        )
        # Update conversation's updated_at
        Conversation.objects.filter(id=self.conversation_id).update(
            updated_at=timezone.now()
        )
        return message

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit an existing message"""
        try:
            message = Message.objects.get(
                id=message_id,
                author=self.user,
                conversation_id=self.conversation_id,
                is_deleted=False
            )
            message.edit(new_content)
            return message
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def delete_message(self, message_id):
        """Soft delete a message"""
        try:
            message = Message.objects.get(
                id=message_id,
                author=self.user,
                conversation_id=self.conversation_id
            )
            message.soft_delete()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message_statuses(self, message):
        """Create message status entries for all conversation participants"""
        participants = UserConversation.objects.filter(
            conversation_id=self.conversation_id,
            left_at__isnull=True
        ).exclude(user=self.user)

        statuses = [
            MessageStatus(
                message=message,
                user=uc.user,
                status='sent'
            )
            for uc in participants
        ]
        MessageStatus.objects.bulk_create(statuses)

    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """Mark multiple messages as read"""
        MessageStatus.objects.filter(
            message_id__in=message_ids,
            user=self.user
        ).update(
            status='read',
            read_at=timezone.now()
        )

        # Update last_read_at for user conversation
        UserConversation.objects.filter(
            user=self.user,
            conversation_id=self.conversation_id
        ).update(last_read_at=timezone.now())

    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        """Add a reaction to a message"""
        from .models import Reaction
        Reaction.objects.get_or_create(
            message_id=message_id,
            user=self.user,
            emoji=emoji
        )

    @database_sync_to_async
    def remove_reaction(self, message_id, emoji):
        """Remove a reaction from a message"""
        from .models import Reaction
        Reaction.objects.filter(
            message_id=message_id,
            user=self.user,
            emoji=emoji
        ).delete()

    @database_sync_to_async
    def set_typing_indicator(self):
        """Set typing indicator for user"""
        TypingIndicator.objects.update_or_create(
            conversation_id=self.conversation_id,
            user=self.user,
            defaults={'started_at': timezone.now()}
        )

    @database_sync_to_async
    def clear_typing_indicator(self):
        """Clear typing indicator for user"""
        TypingIndicator.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).delete()

    @database_sync_to_async
    def update_online_status(self, online=True):
        """Update user's online status"""
        from .models import OnlineStatus, Conversation

        status, _ = OnlineStatus.objects.get_or_create(user=self.user)
        if online:
            status.go_online()
            conversation = Conversation.objects.get(id=self.conversation_id)
            status.update_activity(conversation=conversation)
        else:
            status.go_offline()

    @database_sync_to_async
    def touch_online_activity(self):
        from .models import OnlineStatus, Conversation

        status, _ = OnlineStatus.objects.get_or_create(user=self.user)
        conversation = Conversation.objects.get(id=self.conversation_id)
        status.touch_activity(conversation=conversation)

    async def broadcast_presence_safe(self):
        try:
            await self.broadcast_presence()
        except Exception as exc:
            print('presence broadcast skipped:', exc)

    async def broadcast_presence(self):
        from .services.presence import notify_presence_changed, serialize_user_presence

        if not self.channel_layer:
            return
        presence = await self.get_presence_dict()
        notify_presence_changed(self.user.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'presence_update',
                'user_id': self.user.id,
                'is_online': presence['is_online'],
                'label': presence['label'],
                'last_seen_at': presence['last_seen_at'],
            },
        )

    @database_sync_to_async
    def get_presence_dict(self):
        from .services.presence import serialize_user_presence
        return serialize_user_presence(self.user)

    async def presence_update(self, event):
        if event.get('user_id') == self.user.id:
            return
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_id': event['user_id'],
            'is_online': event['is_online'],
            'label': event['label'],
            'last_seen_at': event.get('last_seen_at'),
        }))

    @database_sync_to_async
    def message_to_dict(self, message):
        """Convert message object to dictionary"""
        from .models import Attachment
        data = {
            'id': message.id,
            'author_id': message.author.id if message.author else None,
            'author_username': (message.author.get_full_name() or message.author.username) if message.author else 'Система',
            'content': message.content,
            'type': message.type,
            'created_at': message.created_at.isoformat(),
            'is_edited': message.is_edited,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            'reply_to_id': message.reply_to_id,
            'is_pinned': message.is_pinned,
            'forwarded_from_id': message.forwarded_from_id,
        }
        atts = list(Attachment.objects.filter(message=message))
        if atts:
            data['attachments'] = [{
                'id': a.id,
                'url': a.file.url,
                'download_url': f'/chat/api/attachment/{a.id}/download/',
                'name': a.file_name,
                'size': a.file_size,
                'type': a.file_type,
                'mime': a.mime_type,
            } for a in atts]
        if message.reply_to_id:
            try:
                orig = Message.objects.select_related('author').get(pk=message.reply_to_id)
                data['reply_to_preview'] = {
                    'author': (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система',
                    'content': (orig.content[:80] + '...') if len(orig.content) > 80 else orig.content,
                }
            except Message.DoesNotExist:
                pass
        if message.forwarded_from_id:
            try:
                orig = Message.objects.select_related('author').get(pk=message.forwarded_from_id)
                data['forwarded_from_author'] = (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система'
            except Message.DoesNotExist:
                pass
        return data

    async def handle_pin_message(self, data):
        """Handle pin/unpin message."""
        message_id = data.get('message_id')
        result = await self.toggle_pin(message_id)
        if result is not None:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_pinned',
                    'message_id': message_id,
                    'is_pinned': result,
                    'user_id': self.user.id,
                }
            )

    async def message_pinned(self, event):
        """Send pin update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message_pinned',
            'message_id': event['message_id'],
            'is_pinned': event['is_pinned'],
        }))

    @database_sync_to_async
    def toggle_pin(self, message_id):
        try:
            msg = Message.objects.get(id=message_id, conversation_id=self.conversation_id)
            msg.is_pinned = not msg.is_pinned
            msg.save(update_fields=['is_pinned'])
            return msg.is_pinned
        except Message.DoesNotExist:
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Handles: new message notifications, mentions, system notifications
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']

        # Reject anonymous users
        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_notification_group = f'notifications_{self.user.id}'

        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_notification_group,
            self.channel_name
        )

        await self.accept()
        await self.update_global_online_status(online=True)

        counts = await self.get_initial_counts()
        if counts:
            await self.send(text_data=json.dumps({
                'type': 'counts_update',
                'counts': counts,
            }))

    @database_sync_to_async
    def get_initial_counts(self):
        from chat.realtime import get_unread_summary
        return get_unread_summary(self.user)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.update_global_online_status(online=False)
        await self.channel_layer.group_discard(
            self.user_notification_group,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get('type') == 'heartbeat':
            await self.touch_global_activity()

    @database_sync_to_async
    def update_global_online_status(self, online=True):
        from .models import OnlineStatus
        from .services.presence import notify_presence_changed

        status, _ = OnlineStatus.objects.get_or_create(user=self.user)
        if online:
            status.go_online()
            status.update_activity()
        else:
            status.go_offline()
        notify_presence_changed(self.user.id)

    @database_sync_to_async
    def touch_global_activity(self):
        from .models import OnlineStatus

        status, _ = OnlineStatus.objects.get_or_create(user=self.user)
        status.touch_activity()

    async def notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

    async def user_event(self, event):
        """Generic real-time payload (badges, inbox, notifications)."""
        await self.send(text_data=json.dumps(event['payload']))
