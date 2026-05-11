from rest_framework import serializers
from .models import (
    DocumentCategory, Document, DocumentVersion,
    DocumentAcknowledgement, DocumentAccessRule
)


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Сериализатор категории документов"""
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'slug', 'description',
            'parent', 'full_path',
            'retention_days', 'icon', 'color',
            'is_active', 'order', 'documents_count'
        ]

    def get_documents_count(self, obj):
        return obj.documents.filter(status='active').count()


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Сериализатор версии документа"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'version_number', 'file', 'file_url',
            'file_name', 'file_size', 'file_hash', 'mime_type',
            'is_scanned', 'scan_result',
            'uploaded_by', 'uploaded_by_name',
            'uploaded_at', 'comment', 'page_count'
        ]
        read_only_fields = ['version_number', 'file_hash', 'uploaded_at']

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class DocumentListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор документа для списков"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_number', 'document_date',
            'document_type', 'document_type_display',
            'category', 'category_name',
            'status', 'status_display',
            'confidentiality',
            'author', 'author_name',
            'views_count', 'updated_at'
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор документа"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_path = serializers.CharField(source='category.get_full_path', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    curator_name = serializers.CharField(source='curator.get_full_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    confidentiality_display = serializers.CharField(source='get_confidentiality_display', read_only=True)
    current_version = serializers.SerializerMethodField()
    versions_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description',
            'document_type', 'document_type_display',
            'category', 'category_name', 'category_path',
            'document_number', 'document_date',
            'effective_date', 'expiry_date',
            'basis', 'confidentiality', 'confidentiality_display',
            'status', 'status_display',
            'author', 'author_name',
            'curator', 'curator_name',
            'tezis_link', 'tezis_id',
            'is_legal_hold', 'legal_hold_reason', 'legal_hold_until',
            'tags', 'views_count',
            'current_version', 'versions_count',
            'created_at', 'updated_at', 'published_at'
        ]

    def get_current_version(self, obj):
        version = obj.get_current_version()
        if version:
            return DocumentVersionSerializer(version).data
        return None

    def get_versions_count(self, obj):
        return obj.versions.count()


class DocumentAcknowledgementSerializer(serializers.ModelSerializer):
    """Сериализатор ознакомления с документом"""
    document_title = serializers.CharField(source='document.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_acknowledged = serializers.SerializerMethodField()

    class Meta:
        model = DocumentAcknowledgement
        fields = [
            'id', 'document', 'document_title',
            'user', 'user_name',
            'required', 'deadline',
            'acknowledged_at', 'is_acknowledged'
        ]
        read_only_fields = ['acknowledged_at']

    def get_is_acknowledged(self, obj):
        return obj.acknowledged_at is not None


class DocumentAccessRuleSerializer(serializers.ModelSerializer):
    """Сериализатор правила доступа"""
    target_display = serializers.SerializerMethodField()
    subject_display = serializers.SerializerMethodField()

    class Meta:
        model = DocumentAccessRule
        fields = [
            'id', 'document', 'category',
            'role', 'department', 'user',
            'target_display', 'subject_display',
            'can_view', 'can_download', 'can_edit',
            'can_delete', 'can_publish', 'can_manage_access',
            'created_at'
        ]
        read_only_fields = ['created_at']

    def get_target_display(self, obj):
        if obj.document:
            return f'Документ: {obj.document.title}'
        if obj.category:
            return f'Категория: {obj.category.name}'
        return 'Все документы'

    def get_subject_display(self, obj):
        if obj.user:
            return f'Пользователь: {obj.user.get_full_name()}'
        if obj.department:
            return f'Подразделение: {obj.department.name}'
        if obj.role:
            return f'Роль: {obj.role}'
        return 'Все'


