from .models import Notification

def notifications_context(request):
    if request.user.is_authenticated:
        # Get all notifications for the user (for the global notification bell)
        # Show recent notifications in the dropdown, but count all unread
        unread_count = Notification.objects.filter(
            receiver=request.user,
            status='unread'
        ).count()

        # Show recent 10 notifications in the dropdown regardless of category
        notifications = Notification.objects.filter(
            receiver=request.user
        ).order_by('-timestamp')[:10]
    else:
        unread_count = 0
        notifications = []

    return {
        'unread_notifications_count': unread_count,
        'notifications_list': notifications
    }
