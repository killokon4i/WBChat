class AuditService:
    """Логирование доступа к статьям"""

    @staticmethod
    def log(article, user, action, details='', ip_address=None):
        from knowledge.models import AuditLog
        AuditLog.objects.create(
            article=article,
            user=user,
            action=action,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def get_article_log(article, limit=50):
        from knowledge.models import AuditLog
        return AuditLog.objects.filter(
            article=article
        ).select_related('user')[:limit]

    @staticmethod
    def get_user_log(user, limit=50):
        from knowledge.models import AuditLog
        return AuditLog.objects.filter(
            user=user
        ).select_related('article')[:limit]
