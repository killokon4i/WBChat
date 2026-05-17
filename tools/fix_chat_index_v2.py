# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "templates/chat/index.html"
t = p.read_text(encoding="utf-8")

start = t.index("{% block content %}")
end = t.index("<!-- New Chat Modal -->")
tail = t[end:]

body = r'''{% block content %}
<div class="wb-portal-mesh-page wb-portal-marketing wb-list-page chat-page chat-page--split">
    <div class="chat-split-layout{% if active_conversation_id %} chat-has-active{% endif %}"
         id="chatSplitLayout"
         data-initial-chat="{% if active_conversation_id %}{{ active_conversation_id }}{% endif %}">
        <aside class="chat-split-sidebar" aria-label="Список чатов">
            <div class="chat-split-sidebar-head">
                <h1 id="chats-page-title">Чаты</h1>
                <motion class="chat-split-sidebar-actions">
                    <button type="button" class="new-chat-btn new-chat-btn--dark" onclick="openGroupModal()" title="Создать беседу">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                            <circle cx="9" cy="7" r="4"/>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                        </svg>
                    </button>
                    <button type="button" class="new-chat-btn new-chat-btn--pink" onclick="openNewChatModal()" title="Начать личный чат">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <line x1="12" y1="5" x2="12" y2="19"/>
                            <line x1="5" y1="12" x2="19" y2="12"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="chat-split-list-wrap">
{% if conversations %}
<div class="chat-list">
    {% for conversation in conversations %}
    <a href="{% url 'chat_index' %}?c={{ conversation.id }}"
       class="chat-item{% if active_conversation_id == conversation.id %} is-active{% endif %}"
       data-conversation-id="{{ conversation.id }}"
       data-conversation-name="{{ conversation.display_name|escapejs }}">
        {% if conversation.display_avatar %}
            <img src="{{ conversation.display_avatar.url }}" alt="" class="chat-avatar">
        {% else %}
            <div class="chat-avatar-placeholder">
                {{ conversation.display_name|slice:":1"|upper }}
            </div>
        {% endif %}
        <div class="chat-info">
            <div class="chat-header">
                <span class="chat-name">
                    {{ conversation.display_name }}
                    {% if conversation.display_position %}
                        <span class="chat-position">{{ conversation.display_position }}</span>
                    {% endif %}
                </span>
                <span class="chat-time">{{ conversation.updated_at|date:"d.m H:i" }}</span>
            </div>
            <div class="chat-preview">
                <span class="chat-last-message">
                    <span class="chat-type-badge chat-type-{{ conversation.type }}">
                        {% if conversation.type == 'direct' %}
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                                <circle cx="12" cy="7" r="4"/>
                            </svg>
                            Личные
                        {% elif conversation.type == 'group' %}
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                            </svg>
                            Группа
                        {% else %}
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                            Канал
                        {% endif %}
                    </span>
                </span>
                {% if conversation.unread_count > 0 %}
                    <span class="chat-unread">{{ conversation.unread_count }}</span>
                {% endif %}
            </div>
        </div>
    </a>
    {% endfor %}
</motion>
{% else %}
<div class="chat-split-list-empty"><p>Нет активных чатов</p></div>
{% endif %}
            </div>
        </aside>
        <main class="chat-split-panel" aria-label="Окно чата">
            <button type="button" class="chat-split-mobile-back" id="chatMobileBack">&#8592; К списку</button>
            <div class="chat-split-empty{% if active_conversation_id %} is-hidden{% endif %}" id="chatPanelEmpty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h2>Выберите чат</h2>
                <p>Нажмите на беседу слева</p>
            </div>
            <iframe class="chat-split-frame{% if active_conversation_id %} is-visible{% endif %}"
                    id="chatPanelFrame"
                    title="Переписка"
                    {% if active_conversation_id %}src="{% url 'chat_room' active_conversation_id %}?embed=1"{% endif %}></iframe>
        </main>
    </div>
</div>

'''

body = body.replace("<motion ", "<div ").replace("</motion>", "</div>")

t = t[:start] + body + tail

t = t.replace(
    "window.location.href = '/chat/' + data.conversation_id + '/';",
    "closeGroupModal();\n            window.location.href = '/chat/?c=' + data.conversation_id;",
)
if "ChatShell.openChat" not in t:
    t = t.replace(
        'onclick="window.location.href=\'${anchorHref}\'"',
        'onclick="if(window.ChatShell){ChatShell.openChat(${convId});}else{window.location.href=\'/chat/?c=${convId}\';} hideChatContextMenu();"',
)

if "chat-shell.js" not in t:
    t = t.rstrip() + """

{% block extra_scripts %}
{% load static %}
<script src="{% static 'js/chat-shell.js' %}?v=4"></script>
{% endblock %}
"""

p.write_text(t, encoding="utf-8")
out = p.read_text(encoding="utf-8")
assert "chatSplitLayout" in out
assert "endfor" in out
assert "motion" not in out
print("OK fixed", p)
