from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Conversation, UserConversation, Message, MessageStatus, Reaction
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    UserConversationSerializer,
    CreateConversationSerializer,
    ReactionSerializer,
    UserSerializer
)

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    """
    API для работы с чатами/беседами
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return CreateConversationSerializer
        return ConversationDetailSerializer
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True
        ).prefetch_related('participants').order_by('-updated_at')
    
    def create(self, request, *args, **kwargs):
        serializer = CreateConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Создаём беседу
        conversation = Conversation.objects.create(
            type=data['type'],
            name=data.get('name', ''),
            description=data.get('description', ''),
            created_by=request.user
        )
        
        # Добавляем создателя как владельца
        UserConversation.objects.create(
            user=request.user,
            conversation=conversation,
            role='owner'
        )
        
        # Добавляем участников
        for user_id in data.get('participant_ids', []):
            try:
                user = User.objects.get(id=user_id)
                if user != request.user:
                    UserConversation.objects.create(
                        user=user,
                        conversation=conversation,
                        role='member'
                    )
            except User.DoesNotExist:
                pass
        
        return Response(
            ConversationDetailSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Получить сообщения чата с пагинацией"""
        conversation = self.get_object()
        
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        messages = conversation.messages.filter(
            is_deleted=False
        ).select_related('author').order_by('-created_at')[offset:offset + limit]
        
        return Response({
            'messages': MessageSerializer(reversed(list(messages)), many=True).data,
            'has_more': conversation.messages.filter(is_deleted=False).count() > offset + limit
        })
    
    @action(detail=True, methods=['post'])
    def add_members(self, request, pk=None):
        """Добавить участников в чат"""
        conversation = self.get_object()
        
        # Проверяем права
        user_conv = UserConversation.objects.filter(
            user=request.user,
            conversation=conversation
        ).first()
        
        if not user_conv or user_conv.role not in ['owner', 'admin']:
            return Response(
                {'error': 'Недостаточно прав'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_ids = request.data.get('user_ids', [])
        added = []
        
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                _, created = UserConversation.objects.get_or_create(
                    user=user,
                    conversation=conversation,
                    defaults={'role': 'member'}
                )
                if created:
                    added.append(user_id)
            except User.DoesNotExist:
                pass
        
        return Response({'added': added})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Покинуть чат"""
        conversation = self.get_object()
        now = timezone.now()

        UserConversation.objects.filter(
            user=request.user,
            conversation=conversation,
        ).update(left_at=now, history_cleared_at=now)

        return Response({'status': 'left'})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Отметить чат как прочитанный"""
        conversation = self.get_object()
        
        user_conv = UserConversation.objects.filter(
            user=request.user,
            conversation=conversation
        ).first()
        
        if user_conv:
            user_conv.mark_as_read()
        
        return Response({'status': 'marked'})


class MessageViewSet(viewsets.ModelViewSet):
    """
    API для работы с сообщениями
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        return Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False,
            conversation__participants=self.request.user
        ).select_related('author').order_by('created_at')
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_pk')
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )
        
        message = serializer.save(
            author=self.request.user,
            conversation=conversation
        )
        
        # Обновляем updated_at у беседы
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        # Создаём статусы для всех участников
        participants = UserConversation.objects.filter(
            conversation=conversation,
            left_at__isnull=True
        ).exclude(user=self.request.user)
        
        MessageStatus.objects.bulk_create([
            MessageStatus(message=message, user=uc.user, status='sent')
            for uc in participants
        ])
    
    @action(detail=True, methods=['post'])
    def react(self, request, conversation_pk=None, pk=None):
        """Добавить/убрать реакцию"""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'Emoji required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reaction, created = Reaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji
        )
        
        if not created:
            reaction.delete()
            return Response({'status': 'removed'})
        
        return Response({'status': 'added'})
    
    @action(detail=True, methods=['post'])
    def edit(self, request, conversation_pk=None, pk=None):
        """Редактировать сообщение"""
        message = self.get_object()
        
        if message.author != request.user:
            return Response(
                {'error': 'Вы не можете редактировать чужие сообщения'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_content = request.data.get('content', '').strip()
        if not new_content:
            return Response(
                {'error': 'Содержимое не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.edit(new_content)
        return Response(MessageSerializer(message).data)
    
    def perform_destroy(self, instance):
        if instance.author == self.request.user:
            instance.soft_delete()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для поиска пользователей
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.all()
        search = self.request.query_params.get('search', '')
        
        if search:
            queryset = queryset.filter(username__icontains=search)
        
        return queryset.exclude(id=self.request.user.id)[:20]


