"""Инициалы для заглушки аватара."""


def initials_from_user(user):
    if not user:
        return '?'

    first = (getattr(user, 'first_name', None) or '').strip()
    last = (getattr(user, 'last_name', None) or '').strip()

    if first and last:
        return (first[0] + last[0]).upper()

    if first:
        words = first.split()
        if len(words) >= 2:
            return (words[0][0] + words[-1][0]).upper()
        if len(first) >= 2:
            return first[:2].upper()
        return first[0].upper()

    if last:
        words = last.split()
        if len(words) >= 2:
            return (words[0][0] + words[-1][0]).upper()
        if len(last) >= 2:
            return last[:2].upper()
        return last[0].upper()

    full = ''
    if hasattr(user, 'get_full_name'):
        full = (user.get_full_name() or '').strip()
    if full:
        words = full.split()
        if len(words) >= 2:
            return (words[0][0] + words[-1][0]).upper()
        if len(words) == 1 and len(words[0]) >= 2:
            return words[0][:2].upper()
        if words:
            return words[0][0].upper()

    username = (getattr(user, 'username', None) or '?').strip()
    if len(username) >= 2:
        return username[:2].upper()
    return username[0].upper()
