"""
Сервис автоматической модерации комментариев.
Проверяет текст на наличие нецензурной лексики и управляет системой предупреждений.
"""
import re
from django.utils import timezone


class AutoModerationService:
    """
    Сервис автомодерации комментариев.
    
    - Проверяет текст на мат/ругательства
    - Выдаёт предупреждения (3 максимум)
    - Банит возможность комментирования после 3 предупреждений
    """
    
    # Список запрещённых слов и паттернов (русский мат)
    # Используем паттерны для обхода замен букв на цифры/символы
    BAD_WORDS_PATTERNS = [
        # Основные корни
        r'[хx][уy][йеёи|!1lia][а-яa-z]*',
        r'[пp][иi][зz3][дd][а-яa-z]*',
        r'[бb][лl][яЯ9][дd]?[а-яa-z]*',
        r'[еёe][бb6][а-яa-z]*',
        r'[сc][уy][кk][аa][а-яa-z]*',
        r'[мm][уy][дd][аa][а-яa-z]*',
        r'[дd][еe][рp][ьb][мm][оo]?[а-яa-z]*',
        r'[гg][оo0][вv][нnh][оo0а-яa-z]*',
        r'[жzg][оo0][пp][аa][а-яa-z]*',
        r'[зz3][аa][лl][уy][пp][аa]?[а-яa-z]*',
        r'[шщ][лl][юy][хx][аa]?[а-яa-z]*',
        r'[пp][иi][дd][аоo][рp][а-яa-z]*',
        r'[пp][еe][дd][иi][кk]',
        r'[пp][еe][дd][рp][иi][лl][аa]?',
        r'[чc][мm][оo0][а-яa-z]*',
        r'[дd][аa][уy][нnh]',
        r'[дd][еe][бb][иi][лl][а-яa-z]*',
        r'[иi][дd][иi][оo0][тt][а-яa-z]*',
        r'[тt][вv][аa][рp][ьb]',
        r'[у][рp][оo0][дd][а-яa-z]*',
        r'[вv][ыu][бb][лl][яЯ9][дd][оo0]?[кk]?',
        r'[зz3][аa][еe][бb][а-яa-z]*',
        r'[оo0][тt][ъь]?[еe][бb][а-яa-z]*',
        r'[нnh][аa][хx][уy][йиi]',
        r'[пp][оo0][хx][уy][йиi]',
        r'[хx][еe][рp][а-яa-z]*',
        r'[ёe][бb][аa][нnh][а-яa-z]*',
        r'[еe][бb][лl][оo0а]',
        r'[еe][бb][уy][чч][а-яa-z]*',
        r'[ъь]?[еe][бb][а-яa-z]*',
    ]
    
    # Компилируем паттерны для производительности
    _compiled_patterns = None
    
    @classmethod
    def _get_patterns(cls):
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE) 
                for pattern in cls.BAD_WORDS_PATTERNS
            ]
        return cls._compiled_patterns
    
    def check_text(self, text: str) -> tuple[bool, list[str]]:
        """
        Проверить текст на наличие запрещённых слов.
        Сверяем по отдельным словам (fullmatch), чтобы не ловить «небольшой», «ребёнок» и т.п.
        """
        if not text:
            return True, []

        normalized = self._normalize_text(text)
        tokens = re.findall(r'[\w]+', normalized, re.UNICODE) or [normalized]

        found_words = []
        for token in tokens:
            if len(token) < 2:
                continue
            for pattern in self._get_patterns():
                if pattern.fullmatch(token):
                    found_words.append(token)
                    break

        found_words = list(set(found_words))
        return len(found_words) == 0, found_words
    
    def _normalize_text(self, text: str) -> str:
        """
        Нормализация текста для улучшения распознавания.
        Заменяет похожие символы на буквы.
        """
        replacements = {
            '0': 'о',
            '1': 'i',
            '3': 'з',
            '4': 'ч',
            '6': 'б',
            '9': 'я',
            '@': 'а',
            '$': 's',
            '!': 'i',
            '|': 'l',
        }
        
        result = text.lower()
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        return result
    
    def process_comment(self, user, content: str) -> dict:
        """
        Обработать комментарий пользователя.
        
        Args:
            user: Пользователь
            content: Текст комментария
            
        Returns:
            dict с результатом:
            - allowed: bool - разрешён ли комментарий
            - reason: str - причина отказа
            - warning_number: int - номер предупреждения (если выдано)
            - is_banned: bool - забанен ли теперь пользователь
        """
        warnings = getattr(user, 'comment_warnings', 0) or 0
        is_banned = getattr(user, 'is_comments_banned', False)

        # Проверяем бан
        if is_banned:
            return {
                'allowed': False,
                'reason': 'banned',
                'message': 'Возможность комментирования заблокирована за неоднократное нарушение правил.',
                'warning_number': None,
                'is_banned': True,
            }
        
        # Проверяем текст
        is_clean, found_words = self.check_text(content)
        
        if is_clean:
            return {
                'allowed': True,
                'reason': None,
                'message': None,
                'warning_number': None,
                'is_banned': False,
            }
        
        # Текст содержит мат — выдаём предупреждение
        user.comment_warnings = warnings + 1
        warning_number = user.comment_warnings

        if user.comment_warnings >= 3:
            user.is_comments_banned = True
            user.comments_banned_at = timezone.now()
            user.save(update_fields=['comment_warnings', 'is_comments_banned', 'comments_banned_at'])
            
            # Создаём уведомление о бане
            self._send_ban_notification(user)
            
            return {
                'allowed': False,
                'reason': 'banned_now',
                'message': 'Вы получили 3-е предупреждение. Возможность комментирования заблокирована за неоднократное нарушение правил.',
                'warning_number': 3,
                'is_banned': True,
            }
        else:
            user.save(update_fields=['comment_warnings'])
            
            # Создаём уведомление о предупреждении
            self._send_warning_notification(user, warning_number)
            
            return {
                'allowed': False,
                'reason': 'profanity',
                'message': f'Комментарий содержит недопустимую лексику. Предупреждение {warning_number} из 3.',
                'warning_number': warning_number,
                'is_banned': False,
            }
    
    def _send_warning_notification(self, user, warning_number: int):
        """Отправить уведомление о предупреждении"""
        from notifications.models import Notification, NotificationType
        
        notification_type, _ = NotificationType.objects.get_or_create(
            code='moderation_warning',
            defaults={
                'name': 'Предупреждение модерации',
                'title_template': 'Предупреждение за нарушение правил',
                'body_template': '{content}',
                'priority': 'high',
            }
        )
        
        remaining = 3 - warning_number
        
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title='⚠️ Предупреждение за нарушение правил',
            content=f'Ваш комментарий был удалён за использование недопустимой лексики.\n\n'
                    f'Это предупреждение {warning_number} из 3.\n'
                    f'После 3 предупреждений возможность комментирования будет заблокирована.\n\n'
                    f'Осталось предупреждений до блокировки: {remaining}',
        )
    
    def _send_ban_notification(self, user):
        """Отправить уведомление о блокировке"""
        from notifications.models import Notification, NotificationType
        
        notification_type, _ = NotificationType.objects.get_or_create(
            code='moderation_ban',
            defaults={
                'name': 'Блокировка комментариев',
                'title_template': 'Возможность комментирования заблокирована',
                'body_template': '{content}',
                'priority': 'urgent',
            }
        )
        
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title='🚫 Возможность комментирования заблокирована',
            content='Вы получили 3 предупреждения за использование недопустимой лексики.\n\n'
                    'Возможность комментирования заблокирована за неоднократное нарушение правил.\n\n'
                    'Все остальные функции портала остаются доступными.',
        )


