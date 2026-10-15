def inbox(request):
    if not request.user.is_authenticated:
        return {}
    from .models import Share

    return {"inbox_count": Share.objects.filter(recipient=request.user, status=Share.PENDING).count()}
