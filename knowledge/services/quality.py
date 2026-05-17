import re
from urllib.parse import urlparse


class QualityCheckService:
    """Автоматические проверки качества статьи перед публикацией"""

    FORBIDDEN_PHRASES = [
        'todo', 'fixme', 'xxx', 'hack', 'заглушка', 'временно',
    ]
    MAX_PARAGRAPH_LENGTH = 2000
    ALLOWED_ATTACHMENT_TYPES = {
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
        'text/plain', 'text/csv',
    }
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif',
        '.vbs', '.js', '.wsf', '.ps1', '.sh', '.jar',
    }
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    def check_article(self, article):
        """Run all quality checks, return list of {'level': 'warning'|'error', 'message': str}"""
        issues = []
        issues.extend(self._check_broken_images(article.content))
        issues.extend(self._check_missing_alt(article.content))
        issues.extend(self._check_paragraph_length(article.content))
        issues.extend(self._check_forbidden_phrases(article.content))
        issues.extend(self._check_empty_headings(article.content))
        issues.extend(self._check_broken_links(article.content))
        return issues

    def _check_broken_images(self, html):
        issues = []
        for m in re.finditer(r'<img[^>]+src=["\']([^"\']*)["\']', html, re.I):
            src = m.group(1)
            if not src or src.startswith('data:'):
                continue
            if not src.startswith(('http', '/')):
                issues.append({'level': 'warning', 'message': f'Подозрительный путь к изображению: {src[:80]}'})
        return issues

    def _check_missing_alt(self, html):
        issues = []
        for m in re.finditer(r'<img(?![^>]*alt=)[^>]*>', html, re.I):
            issues.append({'level': 'warning', 'message': 'Изображение без alt-текста'})
        return issues

    def _check_paragraph_length(self, html):
        issues = []
        for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.I | re.DOTALL):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if len(text) > self.MAX_PARAGRAPH_LENGTH:
                issues.append({
                    'level': 'warning',
                    'message': f'Абзац слишком длинный ({len(text)} символов, рекомендуется до {self.MAX_PARAGRAPH_LENGTH})'
                })
        return issues

    def _check_forbidden_phrases(self, html):
        issues = []
        text_lower = re.sub(r'<[^>]+>', '', html).lower()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in text_lower:
                issues.append({'level': 'warning', 'message': f'Обнаружена запрещённая фраза: «{phrase}»'})
        return issues

    def _check_empty_headings(self, html):
        issues = []
        for m in re.finditer(r'<h[1-6][^>]*>\s*</h[1-6]>', html, re.I):
            issues.append({'level': 'warning', 'message': 'Пустой заголовок'})
        return issues

    def _check_broken_links(self, html):
        issues = []
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']*)["\']', html, re.I):
            href = m.group(1)
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue
            if href.startswith('http'):
                try:
                    parsed = urlparse(href)
                    if not parsed.netloc:
                        issues.append({'level': 'warning', 'message': f'Некорректная ссылка: {href[:80]}'})
                except Exception:
                    issues.append({'level': 'warning', 'message': f'Не удалось разобрать ссылку: {href[:80]}'})
        return issues

    def validate_attachment(self, file):
        """Validate uploaded file for security. Returns list of errors (empty = OK)."""
        errors = []
        import os
        ext = os.path.splitext(file.name)[1].lower()
        if ext in self.DANGEROUS_EXTENSIONS:
            errors.append(f'Запрещённый тип файла: {ext}')

        if file.size > self.MAX_FILE_SIZE:
            errors.append(f'Файл слишком большой ({file.size // 1024 // 1024} МБ, макс. {self.MAX_FILE_SIZE // 1024 // 1024} МБ)')

        content_type = getattr(file, 'content_type', '')
        if content_type and content_type not in self.ALLOWED_ATTACHMENT_TYPES:
            if ext not in ('.txt', '.csv', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                           '.zip', '.rar', '.7z', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
                errors.append(f'Неподдерживаемый тип файла: {content_type}')
        return errors
