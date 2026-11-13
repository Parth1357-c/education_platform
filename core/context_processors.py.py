from django.contrib.auth.models import User
from repository.models import Chapter, Doubt, Profile

def admin_stats(request):
    """Add stats to admin template context"""
    return {
        'total_chapters': Chapter.objects.count(),
        'total_users': User.objects.count(),
        'paid_users': Profile.objects.filter(is_paid=True).count(),
        'total_doubts': Doubt.objects.count(),
    }
