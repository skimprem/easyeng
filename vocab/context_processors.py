def due(request):
    if not request.user.is_authenticated:
        return {}
    from .services import due_cards

    return {"vocab_due": due_cards(request.user).count()}
