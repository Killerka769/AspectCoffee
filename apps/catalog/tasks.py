from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# ── Review notification tasks ──

@shared_task
def send_admin_new_review_notification(review_id):
    """Notify admins when a new review is submitted."""
    from apps.catalog.models import Review
    from django.conf import settings
    from apps.users.notifications import create_notification, send_logged_email
    from apps.users.models import User, UserNotification
    try:
        review = Review.objects.select_related("product", "user").get(pk=review_id)
    except Review.DoesNotExist:
        return
    product_name = review.product.name
    user_info = review.user.email if review.user else review.author_name or "Аноним"
    stars = "★" * review.rating + "☆" * (5 - review.rating)
    body = (
        f"Новый отзыв на товар: {product_name}\n"
        f"Автор: {user_info}\n"
        f"Рейтинг: {stars} ({review.rating}/5)\n"
    )
    if review.delivery_rating:
        d_stars = "★" * review.delivery_rating + "☆" * (5 - review.delivery_rating)
        body += f"Рейтинг доставки: {d_stars} ({review.delivery_rating}/5)\n"
    if review.delivery_text:
        body += f"Текст отзыва о доставке: {review.delivery_text}\n"
    body += f"\nТекст отзыва:\n{review.text}\n\nПерейти к модерации: /admin/catalog/review/"
    admins = getattr(settings, "ADMINS", [])
    if admins:
        to_email = admins[0][1] if isinstance(admins[0], (list, tuple)) else settings.DEFAULT_FROM_EMAIL
    else:
        to_email = settings.DEFAULT_FROM_EMAIL
    subject = f"[AspectCoffee] Новый отзыв на {product_name}"
    log = send_logged_email(
        recipient=to_email,
        subject=subject,
        body=body,
    )
    for staff in User.objects.filter(is_staff=True, is_active=True).exclude(email__iexact=to_email):
        create_notification(
            user=staff,
            title=subject,
            body=body,
            url="/admin/catalog/review/",
            kind=UserNotification.KIND_INFO,
        )
    return log.success


@shared_task
def send_user_review_published_notification(review_id):
    """Notify user that their review was published."""
    from apps.catalog.models import Review
    from django.conf import settings
    from apps.users.notifications import send_logged_email
    try:
        review = Review.objects.select_related("product", "user").get(pk=review_id)
    except Review.DoesNotExist:
        return
    if not review.user or not review.user.email:
        return
    log = send_logged_email(
        recipient=review.user.email,
        subject=f"[AspectCoffee] Ваш отзыв на {review.product.name} опубликован",
        body=(
            f"Здравствуйте!\n\n"
            f"Ваш отзыв на товар «{review.product.name}» был опубликован.\n"
            f"Спасибо за обратную связь!\n\n"
            f"С уважением, Aspect Coffee"
        ),
    )
    return log.success


@shared_task
def send_user_review_rejected_notification(review_id):
    """Notify user that their review was not published."""
    from apps.catalog.models import Review
    from django.conf import settings
    from apps.users.notifications import send_logged_email
    try:
        review = Review.objects.select_related("product", "user").get(pk=review_id)
    except Review.DoesNotExist:
        return
    if not review.user or not review.user.email:
        return
    log = send_logged_email(
        recipient=review.user.email,
        subject=f"[AspectCoffee] Ваш отзыв на {review.product.name} не прошёл модерацию",
        body=(
            f"Здравствуйте!\n\n"
            f"К сожалению, ваш отзыв на товар «{review.product.name}» не прошёл модерацию.\n"
            f"Пожалуйста, ознакомьтесь с правилами написания отзывов и попробуйте снова.\n\n"
            f"С уважением, Aspect Coffee"
        ),
    )
    return log.success


@shared_task
def check_product_images():
    """Periodic task: verify all product images exist on disk, re-download missing ones."""
    import os
    import logging
    from django.core.management import call_command
    logger = logging.getLogger(__name__)
    from apps.catalog.models import Product
    products = Product.objects.exclude(main_image='').exclude(main_image__isnull=True)
    missing = 0
    for p in products:
        try:
            if not os.path.exists(p.main_image.path):
                missing += 1
        except Exception:
            missing += 1

    if missing == 0:
        logger.info("Image check: all %d images OK", products.count())
        return "All %d images OK" % products.count()

    logger.warning("Image check: %d missing images, running fix...", missing)
    try:
        call_command("check_images", "--fix")
        return "Fixed %d images" % missing
    except Exception as e:
        logger.error("Image fix failed: %s", e)
        return "Error: %s" % e
