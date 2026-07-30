from django.db import migrations, models
import django.db.models.deletion


def backfill_email_notifications(apps, schema_editor):
    User = apps.get_model("users", "User")
    EmailLog = apps.get_model("users", "EmailLog")
    UserNotification = apps.get_model("users", "UserNotification")

    users_by_email = {
        email.lower(): user_id
        for email, user_id in User.objects.filter(is_active=True)
        .exclude(email="")
        .values_list("email", "pk")
    }
    for log in EmailLog.objects.all().iterator():
        user_id = users_by_email.get((log.recipient or "").lower())
        if not user_id:
            continue
        normalized = (log.subject or "").lower()
        kind = "order" if any(word in normalized for word in ("заказ", "оплат", "достав")) else "info"
        notification = UserNotification.objects.create(
            user_id=user_id,
            email_log_id=log.pk,
            title=log.subject,
            body=log.body or "",
            kind=kind,
            is_read=True,
        )
        UserNotification.objects.filter(pk=notification.pk).update(created_at=log.sent_at)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_merge_0002_user_city_0009_bonustransaction"),
    ]

    operations = [
        migrations.CreateModel(
            name="PushSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.TextField(unique=True, verbose_name="Endpoint")),
                ("p256dh", models.TextField(verbose_name="P-256 key")),
                ("auth", models.TextField(verbose_name="Auth key")),
                ("user_agent", models.CharField(blank=True, max_length=500, verbose_name="Устройство")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создана")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлена")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_subscriptions", to="users.user", verbose_name="Пользователь")),
            ],
            options={
                "verbose_name": "Push-подписка",
                "verbose_name_plural": "Push-подписки",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="UserNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Заголовок")),
                ("body", models.TextField(blank=True, verbose_name="Текст")),
                ("url", models.CharField(blank=True, max_length=500, verbose_name="Ссылка")),
                ("kind", models.CharField(choices=[("info", "Информация"), ("reply", "Ответ"), ("order", "Заказ"), ("error", "Ошибка")], default="info", max_length=20, verbose_name="Тип")),
                ("is_read", models.BooleanField(default=False, verbose_name="Прочитано")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="triggered_notifications", to="users.user", verbose_name="Отправитель")),
                ("email_log", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_notification", to="users.emaillog", verbose_name="Лог email")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="users.user", verbose_name="Получатель")),
            ],
            options={
                "verbose_name": "Уведомление пользователя",
                "verbose_name_plural": "Уведомления пользователей",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["user", "is_read", "-created_at"], name="users_usern_user_id_134cff_idx")],
            },
        ),
        migrations.RunPython(backfill_email_notifications, migrations.RunPython.noop),
    ]
