
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline as UnfoldTabularInline
from apps.users.models import (
    User, Address, EmailLog,
    BonusTransaction, PaymentTransaction, UserNotification, PushSubscription,
)
class AddressInline(UnfoldTabularInline):
    model = Address
    extra = 0
    fields = ["label", "city", "street", "apartment", "postal_code", "is_default"]


class PushSubscriptionInline(UnfoldTabularInline):
    model = PushSubscription
    extra = 0
    fields = ["is_active", "user_agent", "created_at", "updated_at"]
    readonly_fields = ["user_agent", "created_at", "updated_at"]


class UserNotificationInline(UnfoldTabularInline):
    model = UserNotification
    fk_name = "user"
    extra = 0
    fields = ["title", "kind", "actor", "is_read", "created_at"]
    readonly_fields = ["title", "kind", "actor", "created_at"]
    show_change_link = True
@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "phone_display", "bonus_points", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "email_confirmed", "phone_confirmed")
    search_fields = ("email", "first_name", "last_name", "phone")
    readonly_fields = ("last_login", "date_joined")
    inlines = [AddressInline, PushSubscriptionInline, UserNotificationInline]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Личные данные"), {"fields": ("first_name", "last_name", "role", "phone", "phone_confirmed", "avatar", "bonus_points", "email_confirmed")}),
        (_("Контакты"), {"fields": ("telegram", "viber", "telegram_id", "viber_id")}),
        (_("Права"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Даты"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ["user", "label", "city", "street", "is_default"]
    list_filter = ["is_default", "city"]
    search_fields = ["user__email", "city", "street", "label"]
    raw_id_fields = ["user"]

class EmailLogAddForm(forms.ModelForm):
    target_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("email"),
        required=False,
        label="Пользователь",
        help_text="Выберите одного пользователя, которому нужно отправить уведомление.",
    )
    send_to_all = forms.BooleanField(
        required=False,
        label="Отправить всем пользователям",
        help_text="Если отмечено — уведомление получат все активные пользователи, поле «Пользователь» игнорируется.",
    )

    class Meta:
        model = EmailLog
        fields = ["subject", "body"]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("send_to_all") and not cleaned.get("target_user"):
            raise forms.ValidationError("Выберите пользователя или отметьте «Отправить всем пользователям».")
        return cleaned


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ["recipient", "subject", "sent_at", "success"]
    list_filter = ["success", "sent_at"]
    search_fields = ["recipient", "subject"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = EmailLogAddForm
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ["recipient", "subject", "body", "sent_at", "success", "error_message"]

    def get_fields(self, request, obj=None):
        if obj is None:
            return ["target_user", "send_to_all", "subject", "body"]
        return ["recipient", "subject", "body", "sent_at", "success", "error_message"]

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        from apps.users.notifications import deliver_email, send_logged_email

        if form.cleaned_data.get("send_to_all"):
            target_users = list(User.objects.filter(is_active=True).exclude(email="").order_by("pk"))
            logs = [
                send_logged_email(
                    recipient=user.email,
                    subject=obj.subject,
                    body=obj.body,
                )
                for user in target_users
            ]
            success_count = sum(log.success for log in logs)
            obj.recipient = f"Все пользователи ({len(target_users)})"
            obj.success = success_count == len(target_users)
            obj.error_message = (
                "" if obj.success
                else f"Не отправлено: {len(target_users) - success_count}"
            )
            super().save_model(request, obj, form, change)
            if obj.success:
                messages.success(request, f"Уведомление отправлено {success_count} пользователям.")
            else:
                messages.warning(
                    request,
                    f"Отправлено {success_count} из {len(target_users)} уведомлений.",
                )
        else:
            recipient = form.cleaned_data["target_user"].email
            obj.recipient = recipient
            obj.success, obj.error_message = deliver_email(
                recipient=recipient,
                subject=obj.subject,
                body=obj.body,
            )
            super().save_model(request, obj, form, change)
            if obj.success:
                messages.success(request, f"Уведомление отправлено на {recipient}.")
            else:
                messages.error(request, f"Не удалось отправить уведомление: {obj.error_message}")


@admin.register(UserNotification)
class UserNotificationAdmin(ModelAdmin):
    list_display = ["user", "title", "kind", "actor", "is_read", "created_at"]
    list_filter = ["kind", "is_read", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "title", "body"]
    autocomplete_fields = ["user", "actor"]
    readonly_fields = ["created_at"]


@admin.register(PushSubscription)
class PushSubscriptionAdmin(ModelAdmin):
    list_display = ["user", "device", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", "created_at", "updated_at"]
    search_fields = ["user__email", "user_agent", "endpoint"]
    readonly_fields = ["endpoint", "p256dh", "auth", "user_agent", "created_at", "updated_at"]

    @admin.display(description="Устройство")
    def device(self, obj):
        return obj.user_agent[:80] or "—"

# @admin.register(Achievement)
# class AchievementAdmin(ModelAdmin):
#     list_display = ["title", "condition_type", "condition_value", "sort_order", "is_active"]
#     list_filter = ["is_active", "condition_type"]
#     search_fields = ["title", "description"]
#     list_editable = ["sort_order", "is_active"]
#     ordering = ["sort_order", "pk"]

# @admin.register(UserAchievement)
# class UserAchievementAdmin(ModelAdmin):
#     list_display = ["user", "achievement", "earned_at"]
#     list_filter = ["achievement", "earned_at"]
#     search_fields = ["user__email", "achievement__title"]
#     raw_id_fields = ["user", "achievement"]
#     readonly_fields = ["earned_at"]
#     ordering = ["-earned_at"]

# @admin.register(DiscountLevel)
# class DiscountLevelAdmin(ModelAdmin):
#     list_display = ["min_amount", "discount_percent", "sort_order", "is_active"]
#     list_display_links = ["min_amount"]
#     list_filter = ["is_active"]
#     list_editable = ["discount_percent", "sort_order", "is_active"]
#     ordering = ["sort_order", "min_amount"]

@admin.register(BonusTransaction)
class BonusTransactionAdmin(ModelAdmin):
    list_display = ["user", "type", "amount", "order", "created_at", "expires_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["user__email", "description"]
    raw_id_fields = ["user", "order"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = ["payment_id", "user", "amount", "status", "provider", "created_at"]
    list_filter = ["status", "provider", "created_at"]
    search_fields = ["payment_id", "user__email", "error_message"]
    readonly_fields = [
        "user", "payment_id", "amount", "status", "provider",
        "created_at", "updated_at", "completed_at", "error_message",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False
