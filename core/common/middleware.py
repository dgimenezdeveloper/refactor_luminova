from django.shortcuts import redirect
from django.urls import reverse

from App_LUMINOVA.models import PasswordChangeRequired

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_paths = [
            reverse("App_LUMINOVA:change_password"),
            reverse("App_LUMINOVA:logout"),
        ]

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated or request.user.is_superuser:
            return response
        if request.path_info.startswith(("/static/", "/media/", "/admin/")):
            return response
        if request.path_info in self.allowed_paths:
            return response
        if PasswordChangeRequired.objects.filter(user=request.user).exists():
            return redirect("App_LUMINOVA:change_password")
        return response
