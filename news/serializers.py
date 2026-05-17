from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import News

User = get_user_model()


class AuthorSerializer(serializers.ModelSerializer):
    """Сериализатор автора"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']
        read_only_fields = fields


class NewsListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка новостей"""
    author = AuthorSerializer(read_only=True)
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'content_preview', 'image',
            'author', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def get_content_preview(self, obj):
        if len(obj.content) > 200:
            return obj.content[:200] + '...'
        return obj.content


class NewsDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор новости"""
    author = AuthorSerializer(read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'content', 'image',
            'author', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class NewsCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/редактирования новости"""
    class Meta:
        model = News
        fields = ['title', 'content', 'image']


