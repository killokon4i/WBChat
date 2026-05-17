from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import RegisterForm, ProfileEditForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash


def home(request):
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('profile')  # куда ведём после логина
        else:
            messages.error(request, "Неверный логин или пароль")

    return render(request, 'accounts/login.html')


@login_required(login_url='login')
def profile_view(request):
    from chat.models import Message, UserConversation
    
    # Считаем реальную статистику
    messages_count = Message.objects.filter(
        author=request.user,
        is_deleted=False
    ).count()
    
    chats_count = UserConversation.objects.filter(
        user=request.user,
        left_at__isnull=True
    ).count()
    
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'messages_count': messages_count,
        'chats_count': chats_count
    })


@login_required(login_url='login')
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def profile_edit(request):
    if request.method == "POST":
        form = ProfileEditForm(request.user, request.POST, request.FILES)

        if form.is_valid():
            user = form.save()

            # НЕ разлогиниваем пользователя, если он менял пароль
            if form.cleaned_data.get("new_password"):
                update_session_auth_hash(request, user)

            return redirect("profile")  # твоя страница профиля

    else:
        # instance передаётся в форму, initial не нужен
        form = ProfileEditForm(request.user)

    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required(login_url='login')
def dashboard(request):
    """Дашборд личного кабинета сотрудника"""
    from chat.models import Message, UserConversation
    from news.models import News
    from notifications.models import Notification
    from documents.models import DocumentAcknowledgement
    from org.services import BirthdayService
    
    # Статистика сообщений и чатов
    message_count = Message.objects.filter(
        author=request.user,
        is_deleted=False
    ).count()
    
    chat_count = UserConversation.objects.filter(
        user=request.user,
        left_at__isnull=True
    ).count()
    
    # Документы к прочтению
    unread_docs = DocumentAcknowledgement.objects.filter(
        user=request.user,
        required=True,
        acknowledged_at__isnull=True
    ).count()
    
    # Непрочитанные уведомления
    notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    # Последние уведомления
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Последние новости (показываем все опубликованные + неопубликованные если нет опубликованных)
    recent_news = News.objects.filter(
        is_published=True
    ).order_by('-published_at', '-created_at')[:5]
    
    # Если нет опубликованных - показываем последние любые
    if not recent_news.exists():
        recent_news = News.objects.all().order_by('-created_at')[:5]
    
    # Ближайшие дни рождения
    birthday_service = BirthdayService()
    birthdays = birthday_service.get_upcoming_birthdays(days=7)[:5]
    
    # База знаний — недавние обновления
    from knowledge.services import RecommendationService
    kb_rec = RecommendationService()
    kb_recent = kb_rec.get_recently_updated(limit=5)
    kb_recommended = kb_rec.get_recommended(request.user, limit=3)
    
    return render(request, 'accounts/dashboard.html', {
        'user': request.user,
        'message_count': message_count,
        'chat_count': chat_count,
        'unread_docs': unread_docs,
        'notifications_count': notifications_count,
        'notifications': notifications,
        'recent_news': recent_news,
        'birthdays': birthdays,
        'kb_recent': kb_recent,
        'kb_recommended': kb_recommended,
    })
