from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("library:list")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Добро пожаловать! Добавьте первый текст для чтения.")
        return redirect("library:list")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def settings_view(request):
    form = ProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Настройки сохранены")
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})
