from django import template

from accounts.avatar_utils import initials_from_user

register = template.Library()


@register.filter
def user_initials(user):
    """Первые буквы имени и фамилии (до 2 символов) для заглушки аватара."""
    return initials_from_user(user)
