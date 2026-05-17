from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, UserConversation, Message, MessageStatus, Reaction

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'department']
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор сообщения"""
    author = UserSerializer(read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    reactions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'author', 'author_id', 'author_username',
            'type', 'content', 'reply_to', 'created_at', 'updated_at',
            'is_edited', 'edited_at', 'is_deleted', 'is_pinned',
            'reactions_count'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'edited_at', 'is_deleted']
    
    def get_reactions_count(self, obj):
        return obj.reactions.count()


class ConversationListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка бесед"""
    participants_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'description', 'avatar',
            'created_at', 'updated_at', 'is_active',
            'participants_count', 'last_message', 'unread_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_participants_count(self, obj):
        # Считаем только актуальных участников (left_at IS NULL)
        return obj.userconversation_set.filter(left_at__isnull=True).count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).last()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100],
                'author': last_msg.author.username if last_msg.author else 'System',
                'created_at': last_msg.created_at.isoformat()
            }
        return None
    
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.get_unread_count(user) if user.is_authenticated else 0


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор беседы"""
    participants = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'description', 'avatar',
            'participants', 'created_at', 'updated_at', 'created_by',
            'is_active', 'is_archived', 'messages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_messages(self, obj):
        messages = obj.messages.filter(is_deleted=False).order_by('-created_at')[:50]
        return MessageSerializer(reversed(list(messages)), many=True).data


class UserConversationSerializer(serializers.ModelSerializer):
    """Сериализатор связи пользователь-беседа"""
    conversation = ConversationListSerializer(read_only=True)
    
    class Meta:
        model = UserConversation
        fields = [
            'conversation', 'role', 'notifications_enabled', 'is_muted',
            'is_pinned', 'last_read_at', 'joined_at', 'can_send_messages'
        ]
        read_only_fields = ['joined_at']


class CreateConversationSerializer(serializers.Serializer):
    """Сериализатор для создания беседы"""
    type = serializers.ChoiceField(choices=Conversation.CONVERSATION_TYPES)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )


class ReactionSerializer(serializers.ModelSerializer):
    """Сериализатор реакций"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Reaction
        fields = ['id', 'message', 'user', 'emoji', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


