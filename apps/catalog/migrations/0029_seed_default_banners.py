from django.db import migrations


def seed_default_banners(apps, schema_editor):
    Banner = apps.get_model("pages", "Banner")

    banners = [
        dict(
            slot="popular_block",
            title="Дарим подарки, делаем скидки",
            description="За каждые 1000 ₽ в заказе вы получаете +1% к накопительной скидке. Максимальная скидка — 15%. При покупке 6 пачек кофе по 250 г дарим кофе или чай.",
            link_url="/catalog/",
            button_label="Выбрать кофе",
            is_active=True,
            order=1,
        ),
        dict(
            slot="popular_block",
            title="Сильная команда",
            description="В нашей команде Q-грейдеры, чемпионы и сертифицированные специалисты SCA. Мы постоянно учимся и участвуем в чемпионатах, чтобы делать ваш кофе лучше.",
            link_url="",
            button_label="",
            is_active=True,
            order=2,
        ),
    ]

    for b in banners:
        if not Banner.objects.filter(slot=b["slot"], title=b["title"]).exists():
            Banner.objects.create(**b)


def remove_default_banners(apps, schema_editor):
    Banner = apps.get_model("pages", "Banner")
    Banner.objects.filter(
        slot="popular_block",
        title__in=["Дарим подарки, делаем скидки", "Сильная команда"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0028_seed_promo_slides"),
        ("pages", "0006_alter_banner_slot"),
    ]

    operations = [
        migrations.RunPython(seed_default_banners, remove_default_banners),
    ]
