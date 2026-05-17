from django import forms
from .models import (
    Article, Category, Tag, FAQ, ArticleComment,
    ArticleTemplate, SuggestedEdit, TermRequest, ArticleAttachment,
)


class ArticleForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label='Теги',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите теги через запятую'
        })
    )
    template_id = forms.ModelChoiceField(
        queryset=ArticleTemplate.objects.filter(is_active=True),
        required=False,
        label='Шаблон',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— без шаблона —'
    )
    extra_categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        label='Доп. рубрики',
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'style': 'height:100px'}),
    )

    class Meta:
        model = Article
        fields = [
            'title', 'content', 'category', 'article_type',
            'excerpt', 'review_period_months'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Заголовок статьи'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control tinymce-editor',
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'article_type': forms.Select(attrs={'class': 'form-control'}),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Краткое описание (авто-генерируется если пусто)'
            }),
            'review_period_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1, 'max': 60
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        if self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                self.instance.tags.values_list('name', flat=True)
            )
            self.fields['extra_categories'].initial = self.instance.categories.values_list('id', flat=True)

    def save(self, commit=True):
        article = super().save(commit=commit)
        if commit:
            self._save_tags(article)
            article.categories.set(self.cleaned_data.get('extra_categories', []))
        return article

    def _save_tags(self, article):
        tag_names = [
            t.strip() for t in self.cleaned_data.get('tags_input', '').split(',')
            if t.strip()
        ]
        tags = []
        for name in tag_names:
            from django.utils.text import slugify
            slug = slugify(name, allow_unicode=True) or name.lower().replace(' ', '-')
            tag = Tag.objects.filter(slug=slug).first() or Tag.objects.filter(name__iexact=name).first()
            if not tag:
                tag = Tag.objects.create(slug=slug, name=name)
            tag.usage_count = tag.articles.count() + 1
            tag.save(update_fields=['usage_count'])
            tags.append(tag)
        article.tags.set(tags)


class ArticlePublishForm(forms.Form):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('review', 'На проверку'),
        ('published', 'Опубликовать'),
        ('archived', 'В архив'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label='Статус')


class CommentForm(forms.ModelForm):
    class Meta:
        model = ArticleComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Написать комментарий... (используйте @имя для упоминания)'
            })
        }


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['category', 'question', 'answer', 'related_article', 'order']
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Вопрос'
            }),
            'answer': forms.Textarea(attrs={
                'class': 'form-control tinymce-editor',
                'id': 'faq-answer'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'related_article': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['related_article'].queryset = Article.objects.filter(status='published')
        self.fields['related_article'].required = False


class SuggestedEditForm(forms.ModelForm):
    class Meta:
        model = SuggestedEdit
        fields = ['title', 'content', 'comment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Предложенный заголовок (оставьте пустым если без изменений)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control tinymce-editor',
            }),
            'comment': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Опишите суть предлагаемых изменений'
            }),
        }


class TermRequestForm(forms.Form):
    term = forms.CharField(max_length=200, label='Термин', widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Новый термин или тег'
    }))
    description = forms.CharField(required=False, label='Описание / обоснование', widget=forms.Textarea(attrs={
        'class': 'form-control', 'rows': 3, 'placeholder': 'Зачем нужен этот термин?'
    }))
    synonyms = forms.CharField(required=False, max_length=500, label='Синонимы', widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Через запятую'
    }))


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = ArticleAttachment
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
