from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт демо-контент для Базы знаний'

    def handle(self, *args, **options):
        author = User.objects.filter(is_active=True).first()
        if not author:
            self.stderr.write('Нет активных пользователей! Создайте хотя бы одного.')
            return

        self.stdout.write(f'Автор контента: {author.get_full_name() or author.username}')

        categories = self._create_categories()
        tags = self._create_tags()
        templates = self._create_templates()
        snippets = self._create_snippets()
        articles = self._create_articles(author, categories, tags)
        faqs = self._create_faqs(author, categories, articles)

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Создано:\n'
            f'  Рубрик: {len(categories)}\n'
            f'  Тегов: {len(tags)}\n'
            f'  Шаблонов: {len(templates)}\n'
            f'  Сниппетов: {len(snippets)}\n'
            f'  Статей: {len(articles)}\n'
            f'  FAQ: {len(faqs)}'
        ))

    def _create_categories(self):
        from knowledge.models import Category

        data = [
            # Корневые
            {'name': 'IT', 'slug': 'it', 'icon': '💻', 'color': '#006f43',
             'description': 'Инструкции по IT-инфраструктуре, ПО, системам и сервисам банка'},
            {'name': 'HR', 'slug': 'hr', 'icon': '👥', 'color': '#ca1d91',
             'description': 'Кадровые процедуры, оформление документов, льготы и компенсации'},
            {'name': 'Продукты Банка', 'slug': 'products', 'icon': '🏦', 'color': '#008a4e',
             'description': 'Справочные материалы по продуктам и сервисам WB Bank'},
            {'name': 'Безопасность', 'slug': 'security', 'icon': '🔒', 'color': '#ff2fb3',
             'description': 'Информационная безопасность, правила работы с данными, антифрод'},
            {'name': 'Новичку', 'slug': 'onboarding', 'icon': '🎓', 'color': '#ca1d91',
             'description': 'Всё необходимое для адаптации нового сотрудника'},
            {'name': 'Процессы', 'slug': 'processes', 'icon': '⚙️', 'color': '#008a4e',
             'description': 'Бизнес-процессы, регламенты, стандарты работы'},
        ]

        cats = {}
        for d in data:
            cat, _ = Category.objects.update_or_create(slug=d['slug'], defaults=d)
            cats[d['slug']] = cat
            self.stdout.write(f'  Рубрика: {cat.name}')

        # Подрубрики IT
        sub_it = [
            {'name': 'Рабочие станции', 'slug': 'it-workstations', 'icon': '🖥️', 'parent': cats['it'],
             'description': 'Настройка компьютеров, периферии, ОС'},
            {'name': 'Сети и VPN', 'slug': 'it-vpn', 'icon': '🌐', 'parent': cats['it'],
             'description': 'Подключение к VPN, настройка сети, Wi-Fi'},
            {'name': 'Корпоративные системы', 'slug': 'it-systems', 'icon': '🔧', 'parent': cats['it'],
             'description': 'АБС, CRM, 1С, внутренние порталы'},
            {'name': 'DevOps', 'slug': 'it-devops', 'icon': '🚀', 'parent': cats['it'],
             'description': 'CI/CD, Docker, Kubernetes, мониторинг'},
        ]
        for d in sub_it:
            cat, _ = Category.objects.update_or_create(slug=d['slug'], defaults=d)
            cats[d['slug']] = cat
            self.stdout.write(f'    - {cat.name}')

        # Подрубрики HR
        sub_hr = [
            {'name': 'Оформление', 'slug': 'hr-docs', 'icon': '📄', 'parent': cats['hr'],
             'description': 'Заявления, справки, кадровое оформление'},
            {'name': 'Обучение', 'slug': 'hr-training', 'icon': '📚', 'parent': cats['hr'],
             'description': 'Корпоративное обучение, курсы, сертификации'},
        ]
        for d in sub_hr:
            cat, _ = Category.objects.update_or_create(slug=d['slug'], defaults=d)
            cats[d['slug']] = cat
            self.stdout.write(f'    - {cat.name}')

        # Подрубрики Продуктов
        sub_prod = [
            {'name': 'Кредитование', 'slug': 'prod-credit', 'icon': '💳', 'parent': cats['products'],
             'description': 'Кредитные продукты, ипотека, автокредит'},
            {'name': 'Вклады и счета', 'slug': 'prod-deposits', 'icon': '🏧', 'parent': cats['products'],
             'description': 'Депозиты, текущие счета, накопительные счета'},
        ]
        for d in sub_prod:
            cat, _ = Category.objects.update_or_create(slug=d['slug'], defaults=d)
            cats[d['slug']] = cat
            self.stdout.write(f'    - {cat.name}')

        # Подрубрика Новичку -> Первые дни
        sub_onb = [
            {'name': 'Первые дни', 'slug': 'onb-first-days', 'icon': '📋', 'parent': cats['onboarding'],
             'description': 'Чек-листы и инструкции для первых рабочих дней'},
        ]
        for d in sub_onb:
            cat, _ = Category.objects.update_or_create(slug=d['slug'], defaults=d)
            cats[d['slug']] = cat
            self.stdout.write(f'    - {cat.name}')

        return cats

    def _create_tags(self):
        from knowledge.models import Tag

        tags_data = [
            {'name': 'VPN', 'slug': 'vpn', 'synonyms': ['ВПН', 'виртуальная частная сеть']},
            {'name': 'Контрагенты', 'slug': 'contragents', 'synonyms': ['контрагент', 'клиент']},
            {'name': 'Обучение', 'slug': 'training', 'synonyms': ['курсы', 'тренинг']},
            {'name': '1С', 'slug': '1c', 'synonyms': ['один эс', 'бухгалтерия']},
            {'name': 'Git', 'slug': 'git', 'synonyms': ['гит', 'github', 'gitlab']},
            {'name': 'Docker', 'slug': 'docker', 'synonyms': ['контейнер', 'докер']},
            {'name': 'Почта', 'slug': 'email', 'synonyms': ['email', 'outlook', 'mail']},
            {'name': 'Пароли', 'slug': 'passwords', 'synonyms': ['пароль', 'аутентификация', 'логин']},
            {'name': 'ДБО', 'slug': 'dbo', 'synonyms': ['дистанционное банковское обслуживание', 'интернет-банк']},
            {'name': 'Отпуск', 'slug': 'vacation', 'synonyms': ['отгул', 'выходной']},
            {'name': 'Антифрод', 'slug': 'antifraud', 'synonyms': ['мошенничество', 'fraud']},
            {'name': 'PostgreSQL', 'slug': 'postgresql', 'synonyms': ['postgres', 'постгрес', 'БД']},
            {'name': 'Безопасность', 'slug': 'security-tag', 'synonyms': ['ИБ', 'защита данных']},
            {'name': 'Адаптация', 'slug': 'adaptation', 'synonyms': ['онбординг', 'вхождение']},
            {'name': 'Python', 'slug': 'python', 'synonyms': ['питон', 'django']},
        ]

        tags = {}
        for d in tags_data:
            tag, _ = Tag.objects.update_or_create(
                slug=d['slug'],
                defaults={'name': d['name'], 'synonyms': d.get('synonyms'), 'is_approved': True}
            )
            tags[d['slug']] = tag

        self.stdout.write(f'  Создано тегов: {len(tags)}')
        return tags

    def _create_templates(self):
        from knowledge.models import ArticleTemplate

        templates_data = [
            {
                'name': 'How-to инструкция',
                'article_type': 'howto',
                'content_template': (
                    '<h2>Цель</h2>\n<p>Опишите, какую задачу решает эта инструкция.</p>\n\n'
                    '<h2>Предварительные требования</h2>\n<ul>\n<li>Требование 1</li>\n<li>Требование 2</li>\n</ul>\n\n'
                    '<h2>Пошаговая инструкция</h2>\n<h3>Шаг 1: Заголовок</h3>\n<p>Описание шага.</p>\n\n'
                    '<h3>Шаг 2: Заголовок</h3>\n<p>Описание шага.</p>\n\n'
                    '<h2>Результат</h2>\n<p>Что должно получиться в итоге.</p>\n\n'
                    '<h2>Возможные проблемы</h2>\n<p>Типичные ошибки и их решения.</p>'
                ),
                'checklist': [
                    'Указана цель инструкции',
                    'Перечислены предварительные требования',
                    'Шаги пронумерованы и содержат скриншоты/примеры',
                    'Описан ожидаемый результат',
                    'Указаны возможные проблемы и решения',
                ],
            },
            {
                'name': 'Процедура / SOP',
                'article_type': 'procedure',
                'content_template': (
                    '<h2>Назначение</h2>\n<p>Для чего существует эта процедура.</p>\n\n'
                    '<h2>Область применения</h2>\n<p>Кто и когда должен использовать.</p>\n\n'
                    '<h2>Ответственные</h2>\n<table><thead><tr><th>Роль</th><th>Ответственность</th></tr></thead>'
                    '<tbody><tr><td>—</td><td>—</td></tr></tbody></table>\n\n'
                    '<h2>Порядок действий</h2>\n<ol>\n<li>Шаг 1</li>\n<li>Шаг 2</li>\n</ol>\n\n'
                    '<h2>Контроль и отчётность</h2>\n<p>Как проверяется выполнение.</p>'
                ),
                'checklist': [
                    'Указано назначение процедуры',
                    'Определена область применения',
                    'Назначены ответственные',
                    'Порядок действий логичен и последователен',
                ],
            },
            {
                'name': 'Траблшутинг',
                'article_type': 'troubleshooting',
                'content_template': (
                    '<h2>Симптомы</h2>\n<p>Как проявляется проблема.</p>\n\n'
                    '<h2>Возможные причины</h2>\n<ul>\n<li>Причина 1</li>\n<li>Причина 2</li>\n</ul>\n\n'
                    '<h2>Диагностика</h2>\n<p>Как определить точную причину.</p>\n\n'
                    '<h2>Решение</h2>\n<h3>Вариант 1</h3>\n<p>Описание решения.</p>\n\n'
                    '<h3>Вариант 2</h3>\n<p>Описание решения.</p>\n\n'
                    '<h2>Эскалация</h2>\n<p>Куда обращаться, если ничего не помогло.</p>'
                ),
                'checklist': [
                    'Описаны симптомы проблемы',
                    'Перечислены возможные причины',
                    'Есть шаги диагностики',
                    'Предложены решения',
                    'Указан путь эскалации',
                ],
            },
        ]

        templates = []
        for d in templates_data:
            t, _ = ArticleTemplate.objects.update_or_create(
                name=d['name'], defaults=d
            )
            templates.append(t)
            self.stdout.write(f'  Шаблон: {t.name}')

        return templates

    def _create_snippets(self):
        from knowledge.models import Snippet

        snippets_data = [
            {
                'key': 'support_contacts',
                'title': 'Контакты техподдержки',
                'content': (
                    '<div class="snippet-contacts">'
                    '<p><strong>IT-поддержка:</strong> {{support_phone}} | {{support_email}}</p>'
                    '<p><strong>Часы работы:</strong> {{work_hours}}</p>'
                    '</div>'
                ),
                'variables': {
                    'support_phone': '+7 (495) 123-45-67 (вн. 1111)',
                    'support_email': 'support@wbbank.ru',
                    'work_hours': 'Пн-Пт 08:00–20:00, Сб 10:00–16:00',
                },
            },
            {
                'key': 'vpn_version',
                'title': 'Текущая версия VPN-клиента',
                'content': '<p>Текущая версия: <strong>{{version}}</strong> (обновлено {{update_date}})</p>',
                'variables': {
                    'version': '4.12.3',
                    'update_date': '15.02.2026',
                },
            },
            {
                'key': 'hr_contacts',
                'title': 'Контакты HR',
                'content': (
                    '<p><strong>HR-отдел:</strong> {{hr_phone}} | {{hr_email}}</p>'
                    '<p><strong>HR-портал:</strong> <a href="{{hr_portal}}">{{hr_portal}}</a></p>'
                ),
                'variables': {
                    'hr_phone': '+7 (495) 123-45-68 (вн. 2222)',
                    'hr_email': 'hr@wbbank.ru',
                    'hr_portal': 'https://hr.wbbank.ru',
                },
            },
        ]

        snippets = []
        for d in snippets_data:
            s, _ = Snippet.objects.update_or_create(key=d['key'], defaults=d)
            snippets.append(s)
            self.stdout.write(f'  Сниппет: {s.title}')

        return snippets

    def _create_articles(self, author, cats, tags):
        from knowledge.models import Article, ArticleVersion

        articles_data = [
            # ============ HOW-TO ============
            {
                'title': 'Как подключиться к корпоративному VPN',
                'slug': 'how-to-connect-vpn',
                'article_type': 'howto',
                'category': cats['it-vpn'],
                'tags': ['vpn', 'passwords'],
                'review_period_months': 6,
                'content': '''
<h2>Цель</h2>
<p>Подключение к корпоративной сети WB Bank через VPN для удалённой работы. VPN обеспечивает защищённый доступ ко всем внутренним ресурсам: почте, файловому серверу, АБС, CRM и порталу.</p>

<h2>Предварительные требования</h2>
<ul>
    <li>Корпоративный ноутбук с установленной ОС Windows 10/11 или macOS 12+</li>
    <li>Учётная запись Active Directory (выдаётся при оформлении)</li>
    <li>Доступ к интернету (мин. 10 Мбит/с)</li>
    <li>Установленный антивирус Kaspersky Endpoint Security</li>
</ul>

<h2>Пошаговая инструкция</h2>

<h3>Шаг 1: Скачайте VPN-клиент</h3>
<p>Перейдите на внутренний портал <a href="https://soft.wbbank.ru">soft.wbbank.ru</a> и скачайте последнюю версию <strong>FortiClient VPN</strong>.</p>
<blockquote>Текущая версия: <strong>4.12.3</strong> (обновлено 15.02.2026)</blockquote>

<h3>Шаг 2: Установите клиент</h3>
<p>Запустите скачанный файл и следуйте инструкциям мастера установки. На шаге выбора компонентов отметьте:</p>
<ul>
    <li>✅ VPN-компонент</li>
    <li>✅ Фильтр веб-трафика</li>
    <li>❌ Антивирусный модуль (уже есть Kaspersky)</li>
</ul>

<h3>Шаг 3: Настройте подключение</h3>
<p>После установки откройте FortiClient и создайте новое VPN-подключение:</p>
<table>
    <thead><tr><th>Параметр</th><th>Значение</th></tr></thead>
    <tbody>
        <tr><td>Имя подключения</td><td>WB Bank VPN</td></tr>
        <tr><td>Сервер</td><td>vpn.wbbank.ru</td></tr>
        <tr><td>Порт</td><td>443</td></tr>
        <tr><td>Тип аутентификации</td><td>SSL-VPN</td></tr>
    </tbody>
</table>

<h3>Шаг 4: Подключитесь</h3>
<p>Введите логин (формат: <code>ivanov.ii</code>) и пароль от AD. При первом подключении потребуется подтверждение через SMS на корпоративный номер.</p>

<pre><code class="language-bash"># Проверка подключения (в терминале)
ping 10.0.1.1
traceroute fileserver.wbbank.local
</code></pre>

<h2>Результат</h2>
<p>После успешного подключения в трее появится зелёный значок FortiClient. Все внутренние ресурсы станут доступны как при работе из офиса.</p>

<h2>Возможные проблемы</h2>
<table>
    <thead><tr><th>Проблема</th><th>Решение</th></tr></thead>
    <tbody>
        <tr><td>Ошибка «Unable to establish connection»</td><td>Проверьте подключение к интернету, отключите сторонний VPN</td></tr>
        <tr><td>Ошибка «Authentication failed»</td><td>Проверьте раскладку клавиатуры, убедитесь что пароль не истёк</td></tr>
        <tr><td>Медленное соединение</td><td>Попробуйте переключиться на мобильный интернет, перезапустите клиент</td></tr>
        <tr><td>Не приходит SMS-код</td><td>Обратитесь в IT-поддержку: <strong>support@wbbank.ru</strong> / вн. 1111</td></tr>
    </tbody>
</table>
''',
            },

            # ============ PROCEDURE / SOP ============
            {
                'title': 'Процедура оформления отпуска',
                'slug': 'vacation-procedure',
                'article_type': 'procedure',
                'category': cats['hr-docs'],
                'tags': ['vacation'],
                'review_period_months': 12,
                'content': '''
<h2>Назначение</h2>
<p>Стандартная процедура оформления ежегодного оплачиваемого отпуска для сотрудников WB Bank. Распространяется на все виды отпусков: основной, дополнительный, без сохранения заработной платы.</p>

<h2>Область применения</h2>
<p>Все штатные сотрудники WB Bank, проработавшие не менее 6 месяцев. Для руководителей уровня Director и выше требуется дополнительное согласование с CEO.</p>

<h2>Ответственные</h2>
<table>
    <thead><tr><th>Роль</th><th>Ответственность</th><th>SLA</th></tr></thead>
    <tbody>
        <tr><td>Сотрудник</td><td>Подача заявления, передача дел замещающему</td><td>Не позднее 14 дней до начала</td></tr>
        <tr><td>Руководитель</td><td>Согласование, назначение замещающего</td><td>3 рабочих дня</td></tr>
        <tr><td>HR-партнёр</td><td>Проверка остатка дней, оформление приказа</td><td>2 рабочих дня</td></tr>
        <tr><td>Бухгалтерия</td><td>Расчёт и начисление отпускных</td><td>3 дня до начала отпуска</td></tr>
    </tbody>
</table>

<h2>Порядок действий</h2>
<ol>
    <li><strong>Проверьте остаток дней отпуска</strong> в личном кабинете HR-портала (<a href="https://hr.wbbank.ru/vacation">hr.wbbank.ru/vacation</a>)</li>
    <li><strong>Согласуйте даты</strong> с непосредственным руководителем устно или в мессенджере</li>
    <li><strong>Создайте заявку</strong> в HR-портале:
        <ul>
            <li>Раздел «Мои заявки» → «Новая заявка» → «Отпуск»</li>
            <li>Укажите тип, даты начала и окончания</li>
            <li>Выберите замещающего сотрудника</li>
        </ul>
    </li>
    <li><strong>Дождитесь согласования</strong> от руководителя (уведомление придёт на почту)</li>
    <li><strong>Передайте дела</strong> замещающему: текущие задачи, пароли от общих аккаунтов, контакты ключевых контрагентов</li>
    <li><strong>Настройте автоответ</strong> в корпоративной почте с указанием замещающего</li>
</ol>

<h2>Контроль и отчётность</h2>
<p>HR-партнёр ежемесячно формирует отчёт по отпускам подразделения. Руководитель обязан обеспечить <strong>не менее 2/3 состава</strong> подразделения на рабочих местах в любой момент.</p>

<blockquote>
<strong>Важно:</strong> Отзыв из отпуска допускается только с письменного согласия сотрудника и оформляется отдельным приказом.
</blockquote>
''',
            },

            # ============ TROUBLESHOOTING ============
            {
                'title': 'Не работает корпоративная почта: диагностика и решение',
                'slug': 'email-troubleshooting',
                'article_type': 'troubleshooting',
                'category': cats['it'],
                'tags': ['email', 'passwords'],
                'review_period_months': 6,
                'content': '''
<h2>Симптомы</h2>
<ul>
    <li>Outlook не загружается или зависает при запуске</li>
    <li>Письма не отправляются / не приходят</li>
    <li>Ошибка «Cannot connect to Exchange Server»</li>
    <li>Веб-версия почты (OWA) не открывается</li>
</ul>

<h2>Возможные причины</h2>
<table>
    <thead><tr><th>Причина</th><th>Вероятность</th><th>Затронутые компоненты</th></tr></thead>
    <tbody>
        <tr><td>Проблемы с сетью / VPN</td><td>🔴 Высокая</td><td>Все сервисы</td></tr>
        <tr><td>Истёк пароль AD</td><td>🟡 Средняя</td><td>Все корпоративные системы</td></tr>
        <tr><td>Повреждён профиль Outlook</td><td>🟡 Средняя</td><td>Только Outlook</td></tr>
        <tr><td>Переполнена квота почтового ящика</td><td>🟢 Низкая</td><td>Отправка писем</td></tr>
        <tr><td>Сбой Exchange Server</td><td>🟢 Низкая</td><td>Все пользователи</td></tr>
    </tbody>
</table>

<h2>Диагностика</h2>

<h3>1. Проверьте подключение к сети</h3>
<pre><code class="language-bash"># Проверка связи с почтовым сервером
ping mail.wbbank.local

# Проверка DNS
nslookup mail.wbbank.local

# Проверка порта
Test-NetConnection mail.wbbank.local -Port 443
</code></pre>

<h3>2. Проверьте статус пароля</h3>
<p>Нажмите <code>Ctrl+Alt+Del</code> → «Сменить пароль». Если система просит сменить пароль — он истёк.</p>

<h3>3. Проверьте квоту ящика</h3>
<p>В OWA (<a href="https://mail.wbbank.ru">mail.wbbank.ru</a>) откройте «Настройки» → «Общие» → «Использование ящика».</p>

<h2>Решение</h2>

<h3>Вариант 1: Проблема с VPN (если работаете удалённо)</h3>
<ol>
    <li>Переподключите VPN</li>
    <li>Если не помогло — перезагрузите FortiClient</li>
    <li>Попробуйте подключиться к резервному серверу: <code>vpn2.wbbank.ru</code></li>
</ol>

<h3>Вариант 2: Пересоздание профиля Outlook</h3>
<ol>
    <li>Закройте Outlook</li>
    <li>Откройте «Панель управления» → «Mail (Microsoft Outlook)»</li>
    <li>Нажмите «Показать профили» → «Добавить»</li>
    <li>Введите email: <code>ivanov.ii@wbbank.ru</code></li>
    <li>Выберите новый профиль как профиль по умолчанию</li>
</ol>

<h3>Вариант 3: Очистка квоты</h3>
<ol>
    <li>Удалите письма из папки «Удалённые»</li>
    <li>Очистите папку «Нежелательная почта»</li>
    <li>Архивируйте старые письма (старше 1 года)</li>
</ol>

<h2>Эскалация</h2>
<p>Если ни одно из решений не помогло:</p>
<ul>
    <li><strong>Уровень 1:</strong> IT-поддержка — <code>support@wbbank.ru</code>, вн. 1111</li>
    <li><strong>Уровень 2:</strong> Группа Exchange — <code>exchange-team@wbbank.ru</code></li>
    <li><strong>Критические сбои:</strong> Дежурный инженер — <code>+7 (495) 123-45-99</code> (24/7)</li>
</ul>
''',
            },

            # ============ CHECKLIST ============
            {
                'title': 'Чек-лист: первый рабочий день нового сотрудника',
                'slug': 'new-employee-checklist',
                'article_type': 'checklist',
                'category': cats['onb-first-days'],
                'tags': ['adaptation'],
                'review_period_months': 6,
                'content': '''
<h2>До первого дня (HR / руководитель)</h2>
<ul>
    <li>☐ Подготовить рабочее место (стол, стул, монитор, периферия)</li>
    <li>☐ Заказать корпоративный ноутбук в IT-отделе</li>
    <li>☐ Создать учётную запись AD (логин, email, доступ к ресурсам)</li>
    <li>☐ Оформить пропуск / СКУД</li>
    <li>☐ Назначить наставника (buddy)</li>
    <li>☐ Подготовить Welcome-пакет</li>
    <li>☐ Добавить в рабочие чаты и рассылки</li>
</ul>

<h2>Первый день</h2>

<h3>Утро (09:00–12:00)</h3>
<ul>
    <li>☐ Встреча с HR: оформление документов, ознакомление с ЛНА</li>
    <li>☐ Экскурсия по офису: кухня, переговорки, зона отдыха, туалеты</li>
    <li>☐ Получение пропуска и Welcome-пакета</li>
    <li>☐ Настройка рабочего места с IT-специалистом:
        <ul>
            <li>☐ Логин в Windows / macOS</li>
            <li>☐ Настройка корпоративной почты (Outlook)</li>
            <li>☐ Установка VPN-клиента</li>
            <li>☐ Доступ к корпоративному порталу</li>
            <li>☐ Установка мессенджера (MyTeam)</li>
        </ul>
    </li>
</ul>

<h3>День (12:00–17:00)</h3>
<ul>
    <li>☐ Обед с командой (знакомство в неформальной обстановке)</li>
    <li>☐ Встреча с руководителем: цели на испытательный срок, ожидания</li>
    <li>☐ Знакомство с наставником: план адаптации на 2 недели</li>
    <li>☐ Изучение обязательных материалов:
        <ul>
            <li>☐ <a href="/knowledge/category/security/">Политика информационной безопасности</a></li>
            <li>☐ <a href="/knowledge/article/vacation-procedure/">Процедура оформления отпуска</a></li>
            <li>☐ Корпоративный кодекс поведения</li>
        </ul>
    </li>
</ul>

<h2>Первая неделя</h2>
<ul>
    <li>☐ Пройти обязательные онлайн-курсы (ИБ, комплаенс, AML)</li>
    <li>☐ Получить доступы к рабочим системам (АБС, CRM, Jira)</li>
    <li>☐ Познакомиться с ключевыми коллегами из смежных отделов</li>
    <li>☐ Первая 1-on-1 встреча с руководителем (пятница)</li>
</ul>

<h2>Первый месяц</h2>
<ul>
    <li>☐ Завершить все обязательные курсы</li>
    <li>☐ Пройти промежуточную оценку с руководителем</li>
    <li>☐ Подготовить краткую презентацию «Что я узнал» для команды</li>
    <li>☐ Заполнить профиль на корпоративном портале (фото, контакты, «О себе»)</li>
</ul>

<blockquote>
<strong>Контакты:</strong><br>
HR-отдел: <code>hr@wbbank.ru</code>, вн. 2222<br>
IT-поддержка: <code>support@wbbank.ru</code>, вн. 1111
</blockquote>
''',
            },

            # ============ ONBOARDING ============
            {
                'title': 'Добро пожаловать в WB Bank: путеводитель новичка',
                'slug': 'welcome-guide',
                'article_type': 'onboarding',
                'category': cats['onboarding'],
                'tags': ['adaptation'],
                'is_pinned': True,
                'review_period_months': 12,
                'content': '''
<h2>Добро пожаловать!</h2>
<p>Мы рады, что вы стали частью команды <strong>WB Bank</strong>. Этот путеводитель поможет вам быстро разобраться в самом важном и комфортно влиться в работу.</p>

<h2>О компании</h2>
<p>WB Bank — современный цифровой банк, ориентированный на технологические инновации. Мы обслуживаем более 5 миллионов клиентов и постоянно растём.</p>
<p>Наши ценности:</p>
<ul>
    <li><strong>Клиент в центре</strong> — все решения принимаются в интересах клиента</li>
    <li><strong>Технологичность</strong> — мы внедряем лучшие IT-решения</li>
    <li><strong>Команда</strong> — мы работаем сообща и поддерживаем друг друга</li>
    <li><strong>Развитие</strong> — мы растём профессионально каждый день</li>
</ul>

<h2>Что нужно сделать в первые дни</h2>
<p>Подробный чек-лист вы найдёте в статье <a href="/knowledge/article/new-employee-checklist/">«Чек-лист первого рабочего дня»</a>. Ключевое:</p>
<ol>
    <li>Получить пропуск и настроить рабочее место</li>
    <li>Познакомиться с командой и наставником</li>
    <li>Пройти обязательные курсы по безопасности</li>
    <li>Изучить основные корпоративные системы</li>
</ol>

<h2>Офис и инфраструктура</h2>
<h3>Расположение</h3>
<p>Главный офис: г. Москва, ул. Примерная, д. 42. Вход со стороны набережной, 2 этаж.</p>

<h3>Схема офиса</h3>
<table>
    <thead><tr><th>Этаж</th><th>Что находится</th></tr></thead>
    <tbody>
        <tr><td>1 этаж</td><td>Ресепшн, переговорные A1-A4, кафе</td></tr>
        <tr><td>2 этаж</td><td>Open space (разработка, аналитика), кухня</td></tr>
        <tr><td>3 этаж</td><td>HR, бухгалтерия, юридический отдел</td></tr>
        <tr><td>4 этаж</td><td>Руководство, зона отдыха, спортзал</td></tr>
    </tbody>
</table>

<h3>Распорядок</h3>
<ul>
    <li><strong>Рабочие часы:</strong> гибкий график, ядро 10:00–17:00</li>
    <li><strong>Обед:</strong> с 12:00 до 14:00 (кафе на 1 этаже, компенсация 500 ₽/день)</li>
    <li><strong>Удалёнка:</strong> до 2 дней в неделю (согласовать с руководителем)</li>
</ul>

<h2>Ключевые контакты</h2>
<table>
    <thead><tr><th>Отдел</th><th>Контакт</th><th>Для чего</th></tr></thead>
    <tbody>
        <tr><td>IT-поддержка</td><td>вн. 1111, support@wbbank.ru</td><td>Техника, доступы, ПО</td></tr>
        <tr><td>HR-отдел</td><td>вн. 2222, hr@wbbank.ru</td><td>Кадры, отпуска, справки</td></tr>
        <tr><td>Бухгалтерия</td><td>вн. 3333, accounting@wbbank.ru</td><td>Зарплата, командировки</td></tr>
        <tr><td>АХО</td><td>вн. 4444, aho@wbbank.ru</td><td>Пропуск, мебель, канцелярия</td></tr>
        <tr><td>Безопасность</td><td>вн. 5555, security@wbbank.ru</td><td>Инциденты ИБ, пропуска</td></tr>
    </tbody>
</table>

<h2>Корпоративные системы</h2>
<ul>
    <li><strong>Портал</strong> — <a href="/">portal.wbbank.ru</a> (новости, справочник, документы)</li>
    <li><strong>Почта</strong> — <a href="https://mail.wbbank.ru">mail.wbbank.ru</a> (Outlook/OWA)</li>
    <li><strong>Мессенджер</strong> — MyTeam (скачать из раздела <a href="/knowledge/category/it-workstations/">Рабочие станции</a>)</li>
    <li><strong>VPN</strong> — FortiClient (инструкция: <a href="/knowledge/article/how-to-connect-vpn/">Как подключиться к VPN</a>)</li>
    <li><strong>Задачи</strong> — Jira (доступ запросить через IT-портал)</li>
</ul>

<h2>Куда обратиться с вопросами?</h2>
<p>Не стесняйтесь спрашивать! В первую очередь — ваш <strong>наставник</strong> (buddy). Также полезно:</p>
<ul>
    <li>Искать ответы в <a href="/knowledge/">Базе знаний</a></li>
    <li>Задать вопрос в общем чате «Новички WB Bank» в MyTeam</li>
    <li>Обратиться к HR-партнёру вашего подразделения</li>
</ul>
''',
            },

            # ============ POLICY ============
            {
                'title': 'Политика информационной безопасности для сотрудников',
                'slug': 'infosec-policy',
                'article_type': 'policy',
                'category': cats['security'],
                'tags': ['security-tag', 'passwords'],
                'review_period_months': 12,
                'content': '''
<h2>Общие положения</h2>
<p>Настоящая политика определяет правила обращения с информацией и IT-ресурсами WB Bank. <strong>Каждый сотрудник обязан</strong> ознакомиться с этим документом и соблюдать изложенные требования.</p>

<h2>Классификация информации</h2>
<table>
    <thead><tr><th>Уровень</th><th>Описание</th><th>Примеры</th><th>Правила обращения</th></tr></thead>
    <tbody>
        <tr><td>🔴 Секретно</td><td>Утечка нанесёт критический ущерб</td><td>Ключи шифрования, данные клиентов</td><td>Только на корпоративных устройствах, передача через защищённые каналы</td></tr>
        <tr><td>🟠 Конфиденциально</td><td>Ограниченный круг лиц</td><td>Финансовые отчёты, бизнес-планы</td><td>Запрет пересылки на личную почту, хранение в защищённых папках</td></tr>
        <tr><td>🟡 ДСП</td><td>Для внутреннего пользования</td><td>Инструкции, регламенты, оргструктура</td><td>Не публиковать в интернете</td></tr>
        <tr><td>🟢 Общедоступно</td><td>Публичная информация</td><td>Вакансии, пресс-релизы</td><td>Без ограничений</td></tr>
    </tbody>
</table>

<h2>Правила работы с паролями</h2>
<ul>
    <li>Минимальная длина — <strong>12 символов</strong></li>
    <li>Обязательно: заглавные + строчные буквы + цифры + спецсимволы</li>
    <li>Смена пароля — каждые <strong>90 дней</strong></li>
    <li><strong>Запрещено:</strong> записывать пароли на бумаге, хранить в незашифрованном виде, использовать один пароль для нескольких систем</li>
    <li>Используйте корпоративный менеджер паролей <strong>KeePass</strong></li>
</ul>

<h2>Правила работы с устройствами</h2>
<ul>
    <li>Блокируйте компьютер при отходе (<code>Win+L</code> / <code>Cmd+Ctrl+Q</code>)</li>
    <li>Не подключайте личные USB-устройства без согласования с ИБ</li>
    <li>Не устанавливайте ПО из непроверенных источников</li>
    <li>О потере/краже корпоративного устройства — немедленно сообщите в ИБ</li>
</ul>

<h2>Правила работы с электронной почтой</h2>
<ul>
    <li>Не открывайте подозрительные вложения и ссылки</li>
    <li>Проверяйте адрес отправителя — мошенники маскируются под коллег</li>
    <li>Не пересылайте конфиденциальные данные на внешние адреса</li>
    <li>При подозрении на фишинг — нажмите «Сообщить о фишинге» в Outlook</li>
</ul>

<h2>Ответственность</h2>
<p>Нарушение политики ИБ влечёт дисциплинарную ответственность вплоть до увольнения. При выявлении утечки данных возможна уголовная ответственность по ст. 183 УК РФ.</p>

<blockquote>
<strong>Инцидент ИБ?</strong> Немедленно сообщите: <code>security@wbbank.ru</code>, вн. 5555, горячая линия 24/7: <code>+7 (495) 123-45-55</code>
</blockquote>
''',
            },

            # ============ HOW-TO (DevOps) ============
            {
                'title': 'Как развернуть приложение в Docker: пошаговое руководство',
                'slug': 'docker-deployment-guide',
                'article_type': 'howto',
                'category': cats['it-devops'],
                'tags': ['docker', 'python', 'git'],
                'review_period_months': 6,
                'content': '''
<h2>Цель</h2>
<p>Контейнеризация Django-приложения с PostgreSQL и Redis для развёртывания в тестовой и production-среде.</p>

<h2>Предварительные требования</h2>
<ul>
    <li>Docker Desktop >= 4.25 (<a href="https://soft.wbbank.ru/docker">скачать</a>)</li>
    <li>Docker Compose v2</li>
    <li>Git (доступ к GitLab)</li>
    <li>Базовое понимание Linux и терминала</li>
</ul>

<h2>Пошаговая инструкция</h2>

<h3>Шаг 1: Создайте Dockerfile</h3>
<pre><code class="language-python"># Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \\
    libpq-dev gcc && \\
    rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY . .

# Статика
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \\
     "--bind", "0.0.0.0:8000", \\
     "--workers", "4"]
</code></pre>

<h3>Шаг 2: Настройте docker-compose.yml</h3>
<pre><code class="language-markup">version: "3.9"
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - static:/app/static
      - media:/app/media

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: wbbank
      POSTGRES_USER: wbbank
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
  static:
  media:
</code></pre>

<h3>Шаг 3: Запустите</h3>
<pre><code class="language-bash"># Сборка и запуск
docker compose up -d --build

# Применение миграций
docker compose exec web python manage.py migrate

# Создание суперпользователя
docker compose exec web python manage.py createsuperuser

# Просмотр логов
docker compose logs -f web
</code></pre>

<h2>Результат</h2>
<p>Приложение доступно по адресу <code>http://localhost:8000</code>. PostgreSQL на порту 5432, Redis на 6379.</p>

<h2>Возможные проблемы</h2>
<table>
    <thead><tr><th>Проблема</th><th>Решение</th></tr></thead>
    <tbody>
        <tr><td>«Port 5432 already in use»</td><td>Остановите локальный PostgreSQL: <code>sudo systemctl stop postgresql</code></td></tr>
        <tr><td>«Permission denied» при сборке</td><td>Добавьте пользователя в группу docker: <code>sudo usermod -aG docker $USER</code></td></tr>
        <tr><td>Миграции не применяются</td><td>Проверьте переменную <code>DATABASE_URL</code> в <code>.env</code></td></tr>
    </tbody>
</table>
''',
            },

            # ============ HOW-TO (1C) ============
            {
                'title': 'Работа с контрагентами в 1С: создание и проверка',
                'slug': '1c-contragents-guide',
                'article_type': 'howto',
                'category': cats['it-systems'],
                'tags': ['1c', 'contragents'],
                'review_period_months': 12,
                'content': '''
<h2>Цель</h2>
<p>Создание нового контрагента в 1С:Предприятие и проверка его данных по ЕГРЮЛ/ЕГРИП перед заключением договора.</p>

<h2>Предварительные требования</h2>
<ul>
    <li>Доступ к 1С:Предприятие (роль «Менеджер по работе с контрагентами»)</li>
    <li>ИНН или ОГРН контрагента</li>
    <li>Реквизиты из договора или письма контрагента</li>
</ul>

<h2>Пошаговая инструкция</h2>

<h3>Шаг 1: Проверьте контрагента</h3>
<p>Прежде чем создавать карточку, проверьте контрагента в сервисах:</p>
<ol>
    <li><strong>ЕГРЮЛ/ЕГРИП:</strong> убедитесь, что организация зарегистрирована и действует</li>
    <li><strong>Реестр ФНС:</strong> проверьте задолженности по налогам</li>
    <li><strong>Реестр недобросовестных поставщиков:</strong> убедитесь в отсутствии записей</li>
</ol>

<h3>Шаг 2: Создайте карточку в 1С</h3>
<ol>
    <li>Откройте: <strong>Справочники → Контрагенты → Создать</strong></li>
    <li>Заполните основные реквизиты:
        <table>
            <thead><tr><th>Поле</th><th>Пример</th><th>Обязательно</th></tr></thead>
            <tbody>
                <tr><td>Наименование</td><td>ООО «ТехноПром»</td><td>✅</td></tr>
                <tr><td>ИНН</td><td>7712345678</td><td>✅</td></tr>
                <tr><td>КПП</td><td>771201001</td><td>✅ (для юр.лиц)</td></tr>
                <tr><td>ОГРН</td><td>1027700000001</td><td>✅</td></tr>
                <tr><td>Юр. адрес</td><td>г. Москва, ул. Ленина, д. 1</td><td>✅</td></tr>
                <tr><td>Банковские реквизиты</td><td>р/с, БИК, кор/с</td><td>✅</td></tr>
            </tbody>
        </table>
    </li>
    <li>Нажмите <strong>«Записать и закрыть»</strong></li>
</ol>

<h3>Шаг 3: Настройте договор</h3>
<ol>
    <li>В карточке контрагента перейдите на вкладку «Договоры»</li>
    <li>Нажмите «Создать» и заполните: номер, дату, валюту, тип взаиморасчётов</li>
    <li>Прикрепите скан договора</li>
</ol>

<h2>Результат</h2>
<p>Контрагент появится в общем справочнике и будет доступен для создания платёжных поручений, счетов и актов.</p>

<h2>Возможные проблемы</h2>
<ul>
    <li><strong>«Контрагент с таким ИНН уже существует»</strong> — проверьте справочник, возможно, его создал другой сотрудник</li>
    <li><strong>Не загружаются данные по ИНН</strong> — проверьте подключение к интернету и лицензию модуля проверки</li>
</ul>
''',
            },
        ]

        created_articles = []
        for d in articles_data:
            tag_slugs = d.pop('tags', [])
            cat = d.pop('category')
            pinned = d.pop('is_pinned', False)

            article, created = Article.objects.update_or_create(
                slug=d['slug'],
                defaults={
                    **d,
                    'category': cat,
                    'author': author,
                    'status': 'published',
                    'published_at': timezone.now() - timedelta(days=len(created_articles) * 3),
                    'is_pinned': pinned,
                    'views_count': 50 + len(created_articles) * 37,
                    'avg_rating': round(3.5 + len(created_articles) * 0.2, 1),
                    'ratings_count': 5 + len(created_articles) * 2,
                }
            )

            article_tags = [tags[s] for s in tag_slugs if s in tags]
            if article_tags:
                article.tags.set(article_tags)

            if created or not article.versions.exists():
                ArticleVersion.objects.get_or_create(
                    article=article,
                    version_number=1,
                    defaults={
                        'title': article.title,
                        'content': article.content,
                        'author': author,
                        'comment': 'Создание статьи',
                    }
                )

            created_articles.append(article)
            status = 'создана' if created else 'обновлена'
            self.stdout.write(f'  Статья [{article.get_article_type_display()}]: {article.title} — {status}')

        return created_articles

    def _create_faqs(self, author, cats, articles):
        from knowledge.models import FAQ

        faqs_data = [
            {
                'question': 'Как сбросить забытый пароль от корпоративной учётной записи?',
                'answer': '''
<p>Есть два способа:</p>
<ol>
    <li><strong>Самостоятельно</strong> через портал <a href="https://password.wbbank.ru">password.wbbank.ru</a> — потребуется ответ на секретный вопрос и код из SMS</li>
    <li><strong>Через IT-поддержку</strong> — позвоните на вн. 1111 или напишите на <code>support@wbbank.ru</code>. Потребуется верификация личности (ФИО, табельный номер, название отдела)</li>
</ol>
<p><strong>Время сброса:</strong> самостоятельно — мгновенно, через IT — до 30 минут в рабочее время.</p>
''',
                'category': cats.get('it'),
                'order': 1,
            },
            {
                'question': 'Как подключиться к Wi-Fi в офисе?',
                'answer': '''
<p>В офисе доступны две сети:</p>
<table>
    <thead><tr><th>Сеть</th><th>Назначение</th><th>Как подключиться</th></tr></thead>
    <tbody>
        <tr><td><strong>WBBank-Corp</strong></td><td>Корпоративная (рабочие устройства)</td><td>Логин и пароль AD, автоматический сертификат</td></tr>
        <tr><td><strong>WBBank-Guest</strong></td><td>Гостевая (личные устройства, посетители)</td><td>Код доступа на ресепшн (меняется ежедневно)</td></tr>
    </tbody>
</table>
<p>Если корпоративная сеть не подключается автоматически — обратитесь в IT-поддержку для установки сертификата.</p>
''',
                'category': cats.get('it'),
                'order': 2,
            },
            {
                'question': 'Сколько дней отпуска мне положено?',
                'answer': '''
<p>Стандартный ежегодный оплачиваемый отпуск — <strong>28 календарных дней</strong>.</p>
<p>Дополнительные дни:</p>
<ul>
    <li>За ненормированный рабочий день: <strong>+3 дня</strong> (указано в трудовом договоре)</li>
    <li>За стаж в WB Bank более 5 лет: <strong>+2 дня</strong></li>
    <li>За стаж более 10 лет: <strong>+5 дней</strong></li>
</ul>
<p>Проверить остаток дней можно в <a href="https://hr.wbbank.ru/vacation">HR-портале</a> → «Мои отпуска».</p>
''',
                'category': cats.get('hr'),
                'order': 1,
                'related_article_slug': 'vacation-procedure',
            },
            {
                'question': 'Как заказать справку с места работы?',
                'answer': '''
<p>Оформить заявку на справку можно через HR-портал:</p>
<ol>
    <li>Перейдите в раздел <a href="https://hr.wbbank.ru/requests">«Мои заявки»</a></li>
    <li>Выберите «Справка» → тип справки (2-НДФЛ, о доходах, о занятости и т.д.)</li>
    <li>Укажите период и назначение</li>
    <li>Нажмите «Отправить»</li>
</ol>
<p><strong>Срок изготовления:</strong></p>
<ul>
    <li>Справка 2-НДФЛ — 1 рабочий день</li>
    <li>Справка о доходах (свободная форма) — 3 рабочих дня</li>
    <li>Копия трудовой книжки — 3 рабочих дня</li>
</ul>
<p>Готовую справку можно забрать в HR-отделе (3 этаж, каб. 315) или получить по корпоративной почте в электронном виде.</p>
''',
                'category': cats.get('hr'),
                'order': 2,
            },
            {
                'question': 'Что делать, если я получил подозрительное письмо?',
                'answer': '''
<p><strong>Не открывайте вложения и не переходите по ссылкам!</strong></p>
<p>Действия при подозрении на фишинг:</p>
<ol>
    <li>Не отвечайте на письмо</li>
    <li>В Outlook нажмите кнопку <strong>«Сообщить о фишинге»</strong> (на панели инструментов)</li>
    <li>Если кнопки нет — перешлите письмо <strong>как вложение</strong> на <code>phishing@wbbank.ru</code></li>
    <li>Если вы уже перешли по ссылке или открыли файл — <strong>немедленно</strong> позвоните в ИБ: вн. 5555</li>
</ol>
<p><strong>Признаки фишинга:</strong></p>
<ul>
    <li>Срочность («Ваш аккаунт будет заблокирован!»)</li>
    <li>Подозрительный адрес отправителя (например, <code>support@wbbank.com.ru.evil.com</code>)</li>
    <li>Просьба ввести пароль по ссылке</li>
    <li>Вложение с расширением <code>.exe</code>, <code>.scr</code>, <code>.bat</code></li>
</ul>
''',
                'category': cats.get('security'),
                'order': 1,
            },
            {
                'question': 'Какие кредитные продукты предлагает WB Bank?',
                'answer': '''
<p>Линейка кредитных продуктов WB Bank:</p>
<table>
    <thead><tr><th>Продукт</th><th>Ставка от</th><th>Сумма до</th><th>Срок до</th></tr></thead>
    <tbody>
        <tr><td>Потребительский кредит</td><td>9.9%</td><td>5 000 000 ₽</td><td>7 лет</td></tr>
        <tr><td>Ипотека</td><td>7.5%</td><td>50 000 000 ₽</td><td>30 лет</td></tr>
        <tr><td>Автокредит</td><td>4.9%</td><td>10 000 000 ₽</td><td>7 лет</td></tr>
        <tr><td>Кредитная карта</td><td>0% (грейс)</td><td>1 000 000 ₽</td><td>бессрочно</td></tr>
        <tr><td>Рефинансирование</td><td>8.9%</td><td>10 000 000 ₽</td><td>10 лет</td></tr>
    </tbody>
</table>
<p>Подробные условия и тарифы — в CRM (раздел «Продукты») или в <a href="/knowledge/category/prod-credit/">рубрике «Кредитование»</a> Базы знаний.</p>
''',
                'category': cats.get('products'),
                'order': 1,
            },
            {
                'question': 'Как получить доступ к новой корпоративной системе?',
                'answer': '''
<p>Порядок получения доступа к корпоративным системам:</p>
<ol>
    <li>Перейдите на <a href="https://servicedesk.wbbank.ru">servicedesk.wbbank.ru</a></li>
    <li>Создайте заявку: <strong>«Запрос доступа»</strong> → выберите систему из списка</li>
    <li>Укажите обоснование (для каких задач необходим доступ)</li>
    <li>Заявка автоматически уходит на согласование:
        <ul>
            <li>Руководитель — 1-2 рабочих дня</li>
            <li>Владелец системы — 1-2 рабочих дня</li>
            <li>ИБ (для критичных систем) — 2-3 рабочих дня</li>
        </ul>
    </li>
    <li>После согласования IT настроит доступ и отправит инструкцию на корпоративную почту</li>
</ol>
<p><strong>Среднее время предоставления:</strong> 3-5 рабочих дней.</p>
''',
                'category': cats.get('it'),
                'order': 3,
            },
        ]

        created_faqs = []
        for d in faqs_data:
            related_slug = d.pop('related_article_slug', None)
            related_article = None
            if related_slug:
                from knowledge.models import Article as Art
                related_article = Art.objects.filter(slug=related_slug).first()

            faq, created = FAQ.objects.update_or_create(
                question=d['question'],
                defaults={
                    **d,
                    'author': author,
                    'related_article': related_article,
                    'helpful_yes': 10 + len(created_faqs) * 5,
                    'helpful_no': 1 + len(created_faqs),
                }
            )
            created_faqs.append(faq)
            self.stdout.write(f'  FAQ: {faq.question[:60]}...')

        return created_faqs
