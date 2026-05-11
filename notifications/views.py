from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import Notification


@login_required
def notifications_list(request):
    """Страница уведомлений"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('notification_type').order_by('-created_at')[:50]
    
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def mark_notification_read(request, notification_id):
    """Отметить уведомление как прочитанное"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)


@login_required
def mark_all_read(request):
    """Отметить все уведомления как прочитанные"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'success': True, 'marked_count': count})


@login_required
def notifications_count_api(request):
    """API для получения количества непрочитанных уведомлений"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})


