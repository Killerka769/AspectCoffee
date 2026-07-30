from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_catalog_parser_task(force=False, update_images=False, category="coffee", limit=0):
    from apps.catalog.models import ParserSetting
    settings = ParserSetting.load()

    if not settings.is_auto_update_enabled and not force:
        logger.info("Auto-update is disabled for catalog parser.")
        return "Disabled"

    logger.info("Starting catalog parser task...")
    try:
        argv = ["run_parser", f"--category={category}"]
        if update_images:
            argv.append("--update-images")
        if limit:
            argv.extend([f"--limit={limit}"])
        call_command(*argv)

        settings.last_run_at = timezone.now()
        settings.save()
        return "Success"
    except Exception as e:
        logger.error(f"Error running catalog parser task: {e}")
        return f"Error: {e}"


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
def send_admin_new_recipe_notification(recipe_id):
    from django.conf import settings

    from apps.catalog.models import Recipe
    from apps.users.models import User, UserNotification
    from apps.users.notifications import create_notification, send_logged_email

    try:
        recipe = Recipe.objects.select_related("author").get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return False

    subject = f"[AspectCoffee] Новый рецепт: {recipe.name}"
    body = (
        f"Пользователь {recipe.author.email if recipe.author else '—'} отправил рецепт "
        f"«{recipe.name}» на модерацию.\n\n"
        f"Перейти к модерации: /admin/catalog/recipe/{recipe.pk}/change/"
    )
    to_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    log = send_logged_email(recipient=to_email, subject=subject, body=body)
    for staff in User.objects.filter(is_staff=True, is_active=True).exclude(email__iexact=to_email):
        create_notification(
            user=staff,
            title=subject,
            body=body,
            url=f"/admin/catalog/recipe/{recipe.pk}/change/",
            kind=UserNotification.KIND_INFO,
        )
    return log.success


@shared_task
def send_user_recipe_published_notification(recipe_id):
    from apps.catalog.models import Recipe
    from apps.users.notifications import send_logged_email

    try:
        recipe = Recipe.objects.select_related("author").get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return False
    if not recipe.author or not recipe.author.email:
        return False

    log = send_logged_email(
        recipient=recipe.author.email,
        subject=f"[AspectCoffee] Ваш рецепт «{recipe.name}» опубликован",
        body=(
            f"Здравствуйте!\n\n"
            f"Ваш рецепт «{recipe.name}» прошёл модерацию и опубликован на сайте.\n\n"
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
