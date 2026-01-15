from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Aplicación de notificaciones: sistema de alertas y comunicación entre módulos."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notificaciones del Sistema"
