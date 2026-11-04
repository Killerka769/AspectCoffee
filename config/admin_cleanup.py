"""Скрытие технических моделей в Django Admin (модели в БД остаются)."""

from django.contrib import admin


def _unregister(model):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


def apply_admin_cleanup():
    # JWT / OAuth / axes — не для контент-менеджеров
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        _unregister(OutstandingToken)
        _unregister(BlacklistedToken)
    except ImportError:
        pass

    try:
        from allauth.socialaccount.models import SocialAccount, SocialToken

        _unregister(SocialAccount)
        _unregister(SocialToken)
    except ImportError:
        pass

    try:
        from allauth.account.models import EmailAddress

        _unregister(EmailAddress)
    except ImportError:
        pass

    try:
        from axes.models import AccessAttempt, AccessLog

        _unregister(AccessAttempt)
        _unregister(AccessLog)
    except ImportError:
        pass

    from apps.catalog.models import ProductView
    from apps.blog.models import BlogPostView, ArticleLike
    from apps.pages.models import CommunityPostLike
    from apps.orders.models import Cart, Wishlist, OrderItem

    for model in (
        ProductView,
        BlogPostView,
        ArticleLike,
        CommunityPostLike,
        Cart,
        Wishlist,
        OrderItem,
    ):
        _unregister(model)

    try:
        from apps.users.models import PushSubscription

        _unregister(PushSubscription)
    except ImportError:
        pass
