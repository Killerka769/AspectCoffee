"""Idempotent demo-data seeder for the Aspect Coffee clone.

Populates the demo content that design-testing needs but the parser does not
create: promo code FRST15, brew methods, flavor notes, approved reviews,
a blog (Журнал), a home-page banner, a community post and SiteSettings.

Usage:  python manage.py seed_demo
Safe to run multiple times (uses get_or_create / existence checks).
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.catalog.models import (
    BrewMethod, FlavorNote, Product, Review, SiteSettings,
)
from apps.orders.models import PromoCode
from apps.blog.models import BlogCategory, BlogPost
from apps.pages.models import Banner, CommunityPost
from apps.users.models import User


class Command(BaseCommand):
    help = "Seed idempotent demo data (promo, reviews, blog, banner, brew methods, flavor notes)."

    def _p(self, msg):
        self.stdout.write(msg)

    def handle(self, *args, **options):
        now = timezone.now()

        # 1. SiteSettings singleton (defaults).
        SiteSettings.load()
        self._p("SiteSettings: ok")

        # 2. Promo code FRST15 (15% off) — used by the cart demo.
        promo, created = PromoCode.objects.get_or_create(
            code="FRST15",
            defaults={
                "discount_type": PromoCode.DISCOUNT_PERCENT,
                "discount_value": 15,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=365),
                "min_order_amount": 0,
                "is_active": True,
            },
        )
        self._p(f"PromoCode FRST15: {'created' if created else 'exists'}")

        # 3. Brew methods (slugs match catalog quick-filters).
        brew = [
            ("Турка", "turka"), ("Эспрессо-машина", "espresso-machine"),
            ("Френч-пресс", "french-press"), ("V60", "v60"),
            ("Гейзерная кофеварка", "geyzer"),
        ]
        brew_objs = [
            BrewMethod.objects.get_or_create(slug=s, defaults={"name": n})[0]
            for n, s in brew
        ]
        self._p(f"BrewMethods: {BrewMethod.objects.count()}")

        # 4. Flavor notes (slugs match catalog flavor filter).
        flavors = [
            ("Шоколад", "shokolad"), ("Орех", "orex"), ("Цитрус", "citrus"),
            ("Ягоды", "yagody"), ("Цветы", "cveti"),
        ]
        flavor_objs = [
            FlavorNote.objects.get_or_create(slug=s, defaults={"name": n})[0]
            for n, s in flavors
        ]
        self._p(f"FlavorNotes: {FlavorNote.objects.count()}")

        # 5. Attach brew methods + flavor notes to the first 20 products.
        for i, product in enumerate(Product.objects.filter(is_active=True)[:20]):
            if not product.brew_methods.exists():
                product.brew_methods.add(*brew_objs[: 2 + i % 3])
            if not product.flavor_notes.exists():
                product.flavor_notes.add(*flavor_objs[: 1 + i % 3])
        self._p("Products: brew methods / flavor notes attached")

        # 6. Approved demo reviews on the first 5 products (only if none yet).
        demo_reviews = [
            (5, "Алексей", "Отличный кофе, насыщенный вкус. Беру повторно."),
            (5, "Елена", "Очень понравился аромат и баланс. Рекомендую к молоку."),
            (4, "Дмитрий", "Хороший сорт за свои деньги, свежая обжарка."),
        ]
        added = 0
        for product in Product.objects.filter(is_active=True)[:5]:
            if product.reviews.exists():
                continue
            for rating, name, text in demo_reviews:
                Review.objects.create(
                    product=product, rating=rating, author_name=name,
                    text=text, is_approved=True,
                )
                added += 1
        self._p(f"Reviews: +{added}")

        # 7. Blog (Журнал) demo content.
        guide, _ = BlogCategory.objects.get_or_create(
            slug="gid", defaults={"name": "Гид"})
        roast, _ = BlogCategory.objects.get_or_create(
            slug="obzharka", defaults={"name": "Обжарка"})
        posts = [
            ("Как выбрать кофе под фильтр", guide,
             "Разбираем плотность, кислотность и обжарку для ежедневного заваривания."),
            ("Почему свежая обжарка важна", roast,
             "Что происходит с кофе после обжарки и когда вкус раскрывается лучше всего."),
            ("Помол для эспрессо и турки", guide,
             "Как понять, что помол слишком крупный или мелкий, без лаборатории."),
        ]
        for title, cat, descr in posts:
            BlogPost.objects.get_or_create(
                slug=slugify(title, allow_unicode=True),
                defaults={
                    "title": title, "category": cat,
                    "short_description": descr,
                    "content": f"<p>{descr}</p><p>Подробный материал скоро будет дополнен.</p>",
                    "is_published": True, "is_featured": True,
                },
            )
        self._p(f"BlogPosts: {BlogPost.objects.count()}")

        # 8. Home "Сорта недели" banner.
        Banner.objects.get_or_create(
            slot="home_weekly", title="Сорта недели со скидкой",
            defaults={
                "description": "Свежая обжарка каждый день. Доставка по всей России.",
                "link_url": "/catalog/", "button_label": "В каталог",
                "is_active": True, "order": 0,
            },
        )
        self._p(f"Banners: {Banner.objects.count()}")

        # 9. A demo community post (needs any user).
        user = User.objects.order_by("id").first()
        if user and not CommunityPost.objects.exists():
            CommunityPost.objects.create(
                user=user, title="Мой рецепт для V60",
                text="18 г кофе на 300 г воды, 92°C, общее время ~2:45. Делюсь — заходит идеально!",
                is_published=True,
            )
        self._p(f"CommunityPosts: {CommunityPost.objects.count()}")

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
