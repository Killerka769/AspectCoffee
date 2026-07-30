
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import CursorPagination
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.throttling import AnonRateThrottle
from apps.catalog.models import Category, Product, Recipe, Review
from apps.catalog.filters import ProductFilter
from apps.orders.models import Cart, CartItem, Order, PromoCode
from apps.users.models import User
from apps.delivery.cdek import CDEKClient
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    RecipeSerializer, ReviewSerializer,
    RegisterSerializer, UserProfileSerializer,
    CartSerializer, CartItemSerializer, PromoApplySerializer,
    OrderSerializer, OrderCreateSerializer,
)
class StandardCursorPagination(CursorPagination):
    ordering = "-created_at"


class SearchSuggestView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        scope = (request.query_params.get("scope") or "catalog").strip()
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])

        results = []
        if scope == "blog":
            try:
                from apps.blog.models import BlogPost
                posts = BlogPost.objects.filter(is_published=True).filter(
                    title__icontains=q
                )[:8]
                for p in posts:
                    image = ""
                    if getattr(p, "cover_image", None):
                        try:
                            image = p.cover_image.url
                        except Exception:
                            image = ""
                    results.append({
                        "title": p.title,
                        "subtitle": (getattr(p, "summary", "") or "")[:80],
                        "url": p.get_absolute_url() if hasattr(p, "get_absolute_url") else f"/blog/{p.slug}/",
                        "image": image,
                        "kind": "Журнал",
                    })
            except Exception:
                pass
        else:
            from apps.catalog.models import Product
            products = (
                Product.objects.filter(is_active=True)
                .filter(name__icontains=q)
                .select_related("category")[:8]
            )
            for p in products:
                image = ""
                if p.main_image:
                    try:
                        image = p.main_image.url
                    except Exception:
                        image = ""
                results.append({
                    "title": p.name,
                    "subtitle": (p.short_description or "")[:80],
                    "url": p.get_absolute_url(),
                    "image": image,
                    "kind": "Каталог",
                })
        return Response(results)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        from django.core.cache import cache
        from django.utils.crypto import get_random_string
        from django.core.mail import send_mail
        token = get_random_string(32)
        cache.set(f"email_verify_{token}", user.id, timeout=86400)
        try:
            send_mail(
                subject="Подтверждение email — Aspect Coffee",
                message=f"Здравствуйте!\n\nДля подтверждения email используйте этот токен:\n{token}\n\nОтправьте его на /api/v1/auth/confirm-email/",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserProfileSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "detail": "Пожалуйста, проверьте почту для подтверждения аккаунта."
        }, status=status.HTTP_201_CREATED)

class EmailConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Токен обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.cache import cache
        user_id = cache.get(f"email_verify_{token}")
        if not user_id:
            return Response({"detail": "Неверный или просроченный токен"}, status=status.HTTP_400_BAD_REQUEST)

        User.objects.filter(id=user_id).update(email_confirmed=True)
        cache.delete(f"email_verify_{token}")
        return Response({"detail": "Email успешно подтверждён!"})

class DeliveryCalcView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        city_to = request.query_params.get("to_city") or ""
        weight_g = request.query_params.get("weight_g") or "500"
        try:
            weight = max(100, min(int(weight_g), 30000))
        except ValueError:
            weight = 500
        client = CDEKClient()
        data = client.calc_tariff_preview(
            from_location={"city": getattr(settings, "CDEK_SENDER_CITY", "Москва")},
            to_location={"city": city_to or "?"},
            packages=[{"weight": weight}],
        )
        return Response(
            {"to_city": city_to, "weight_g": weight, **data},
            status=status.HTTP_200_OK,
        )
class DeliveryPVZView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        city = request.query_params.get("city") or ""
        client = CDEKClient()
        if not client.configured():
            return Response({"city": city, "points": [], "detail": "CDEK credentials not configured"})
        return Response(
            {"city": city, "points": [], "detail": "Implement PVZ listing with authenticated CDEK API"},
            status=status.HTTP_200_OK,
        )
class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True, parent=None).prefetch_related("children")
    lookup_field = "slug"
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related(
        "variants", "images", "tags", "flavor_notes", "brew_methods",
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    lookup_field = "slug"
    pagination_class = StandardCursorPagination
    ordering = ["-created_at"]
    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer
    @action(detail=True, methods=["get"])
    def related(self, request, slug=None):
        product = self.get_object()
        related = product.related_products.filter(is_active=True)[:8]
        serializer = ProductListSerializer(related, many=True, context={"request": request})
        return Response(serializer.data)
    @action(detail=True, methods=["get", "post"],
            authentication_classes=[SessionAuthentication, JWTAuthentication],
            permission_classes=[permissions.AllowAny])
    def reviews(self, request, slug=None):
        product = self.get_object()
        if request.method == "GET":
            reviews = product.reviews.filter(is_approved=True).order_by("-created_at")
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data)
        if not request.user.is_authenticated:
            return Response({"detail": "Необходима авторизация"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Recipe.objects.filter(is_published=True).select_related("brew_method")
    serializer_class = RecipeSerializer
    lookup_field = "slug"
def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart
class CartView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)
class CartItemView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        cart = get_or_create_cart(request)
        serializer = CartItemSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        variant = serializer.validated_data["variant"]
        qty = serializer.validated_data["qty"]
        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if not created:
            item.qty += qty
            item.save()
        return Response(CartSerializer(cart, context={"request": request}).data, status=status.HTTP_201_CREATED)
    def patch(self, request, pk):
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        qty = request.data.get("qty")
        if not qty or int(qty) < 1:
            return Response({"detail": "Количество должно быть ≥ 1"}, status=status.HTTP_400_BAD_REQUEST)
        item.qty = int(qty)
        item.save()
        return Response(CartSerializer(cart, context={"request": request}).data)
    def delete(self, request, pk):
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        item.delete()
        return Response(CartSerializer(cart, context={"request": request}).data)
class CartPromoView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        cart = get_or_create_cart(request)
        serializer = PromoApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        try:
            promo = PromoCode.objects.get(code__iexact=code)
        except PromoCode.DoesNotExist:
            return Response({"detail": "Промо-код не найден"}, status=status.HTTP_404_NOT_FOUND)
        if not promo.is_valid():
            return Response({"detail": "Промо-код недействителен или истёк"}, status=status.HTTP_400_BAD_REQUEST)
        cart.promo_code = promo
        cart.save()
        return Response(CartSerializer(cart, context={"request": request}).data)
class OrderViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardCursorPagination
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items").order_by("-created_at")
    def create(self, request):
        cart = get_or_create_cart(request)
        if not request.user.email_confirmed:
            return Response({"detail": "Для оформления заказа необходимо подтвердить email."}, status=status.HTTP_403_FORBIDDEN)
        if not cart.items.exists():
            return Response({"detail": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            promo = cart.promo_code
            if promo:
                promo = PromoCode.objects.select_for_update().get(id=promo.id)
                if not promo.is_valid():
                    return Response({"detail": "Промо-код недействителен или превышен лимит"}, status=status.HTTP_400_BAD_REQUEST)
                promo.used_count += 1
                promo.save()
            order = Order.objects.create(
                user=request.user,
                delivery_type=data["delivery_type"],
                delivery_address=data["delivery_address"],
                payment_method=data["payment_method"],
                contact_name=data["contact_name"],
                contact_phone=data["contact_phone"],
                contact_email=data["contact_email"],
                comment=data.get("comment", ""),
                promo_code=promo,
                discount_amount=cart.discount_amount,
                total_amount=cart.total,
            )
            for item in cart.items.select_related("variant__product"):
                from apps.orders.models import OrderItem
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    variant_description=str(item.variant),
                    qty=item.qty,
                    price_at_order=item.variant.price,
                )
            cart.items.all().delete()
            cart.promo_code = None
            cart.save()
        from apps.orders.tasks import send_order_confirmation
        try:
            send_order_confirmation.delay(
                order.id,
                order.payment_method in (Order.PAYMENT_CARD, Order.PAYMENT_SBP),
            )
        except Exception:
            pass
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.STATUS_NEW, Order.STATUS_PAID):
            return Response(
                {"detail": "Заказ нельзя отменить на данном этапе"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = Order.STATUS_CANCELLED
        order.save()
        from apps.orders.tasks import send_order_status_email
        try:
            send_order_status_email.delay(order.id, Order.STATUS_CANCELLED)
        except Exception:
            pass
        return Response(OrderSerializer(order).data)
