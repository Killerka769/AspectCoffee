from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'
    verbose_name = 'Блог'

    def ready(self):
        from config.admin_cleanup import apply_admin_cleanup

        apply_admin_cleanup()
