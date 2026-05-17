from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.simple_tag
def article_toc(content):
    """Генерирует HTML-оглавление по заголовкам H2/H3 с дедупликацией якорей"""
    if not content:
        return ''
    from django.utils.text import slugify
    pattern = re.compile(r'<(h[23])([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
    items = []
    used_anchors = set()
    for match in pattern.finditer(content):
        tag = match.group(1).lower()
        text = re.sub(r'<[^>]+>', '', match.group(3)).strip()
        anchor = slugify(text, allow_unicode=True) or f'section-{len(items)}'
        base_anchor = anchor
        counter = 1
        while anchor in used_anchors:
            anchor = f'{base_anchor}-{counter}'
            counter += 1
        used_anchors.add(anchor)
        level = int(tag[1])
        indent = 'padding-left: 16px;' if level == 3 else ''
        items.append(
            f'<a href="#{anchor}" class="toc-link" style="{indent}">{text}</a>'
        )
    if not items:
        return ''
    html = '<nav class="article-toc"><h4>Оглавление</h4>' + ''.join(items) + '</nav>'
    return mark_safe(html)


@register.simple_tag
def breadcrumbs(category):
    """Генерирует хлебные крошки для рубрики"""
    if not category:
        return ''
    crumbs = category.get_breadcrumbs()
    parts = ['<a href="/knowledge/">База знаний</a>']
    for c in crumbs[:-1]:
        parts.append(f'<a href="/knowledge/category/{c.slug}/">{c.name}</a>')
    if crumbs:
        parts.append(f'<span>{crumbs[-1].name}</span>')
    html = ' <span class="bc-sep">→</span> '.join(parts)
    return mark_safe(f'<nav class="breadcrumbs">{html}</nav>')
