# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "templates/chat/index.html"
t = p.read_text(encoding="utf-8")

if "id=\"chatSplitLayout\"" in t:
    print("OK: split layout already present")
else:
    start = t.index("{% block content %}")
    end = t.index("<!-- New Chat Modal -->")
    old = t[start:end]

    new = """{% block content %}
<div class="wb-portal-mesh-page wb-portal-marketing wb-list-page chat-page chat-page--split">
    <div class="chat-split-layout{% if active_conversation_id %} chat-has-active{% endif %}"
         id="chatSplitLayout"
         data-initial-chat="{% if active_conversation_id %}{{ active_conversation_id }}{% endif %}">
        <aside class="chat-split-sidebar" aria-label="Список чатов">
            <div class="chat-split-sidebar-head">
                <h1 id="chats-page-title">Чаты</h1>
                <div class="chat-split-sidebar-actions">
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
"""
    import re

    m = re.search(r"(\{% if conversations %\}.*?\{% endif %\})", old, re.DOTALL)
    if not m:
        raise SystemExit("conversations block not found")
    conv = m.group(1)
    conv = conv.replace(
        "{% url 'chat_room' conversation.id %}",
        "{% url 'chat_index' %}?c={{ conversation.id }}",
    )
    conv = conv.replace(
        'class="chat-item"',
        'class="chat-item{% if active_conversation_id == conversation.id %} is-active{% endif %}"',
    )
    conv = re.sub(
        r"\{% else %\}.*",
        '{% else %}\n<div class="chat-split-list-empty"><p>Нет активных чатов</p></div>\n{% endif %}',
        conv,
        count=1,
        flags=re.DOTALL,
    )

    foot = """
            </div>
        </aside>
        <main class="chat-split-panel" aria-label="Окно чата">
            <button type="button" class="chat-split-mobile-back" id="chatMobileBack">← К списку</button>
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

"""
    t = t[:start] + new + conv + foot + t[end:]
    print("inserted split layout")

t = t.replace(
    "window.location.href = '/chat/' + data.conversation_id + '/';",
    "closeGroupModal();\n            window.location.href = '/chat/?c=' + data.conversation_id;",
)
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
print("written:", p)
print("chatSplitLayout:", "chatSplitLayout" in p.read_text(encoding="utf-8"))
print("chat-shell.js:", "chat-shell.js" in p.read_text(encoding="utf-8"))
