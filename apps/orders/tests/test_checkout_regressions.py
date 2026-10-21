from decimal import Decimal
from unittest.mock import patch

from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings

from apps.catalog.models import Product, ProductVariant, SiteSettings
from apps.orders.models import Cart, CartItem, Order, RecurringOrder
from apps.users.models import Address, User


class CheckoutRegressionTests(TestCase):
    @override_settings(PAYMENT_COD_ENABLED=False)
    def test_disabled_cod_is_hidden_and_rejected_on_server(self):
        self._anonymous_cart()
        response = self.client.get("/basket/")
        self.assertNotContains(response, 'name="payment_method_radio" type="radio" value="cod"')
        response = self._post_checkout(self._checkout_data())
        self.assertEqual(response.status_code, 400)
        self.assertIn("Оплата при получении недоступна", response.json()["error"])
        self.assertFalse(Order.objects.exists())

    def setUp(self):
        self.site_settings = SiteSettings.load()
        self.site_settings.enable_pickup = True
        self.site_settings.save(update_fields=["enable_pickup"])
        self.product = Product.objects.create(name="Тестовый сорт", slug="test-sort")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight=250,
            price=Decimal("500.00"),
            stock_qty=10,
        )

    def _anonymous_cart(self):
        session = self.client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, variant=self.variant, qty=1)
        return cart

    def _user_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        CartItem.objects.create(cart=cart, variant=self.variant, qty=1)
        return cart

    def _checkout_data(self, **overrides):
        data = {
            "action": "checkout",
            "full_name": "Иван Иванов",
            "phone": "9991112233",
            "phone_code": "+7",
            "email": "buyer@example.com",
            "agree_terms": "on",
            "delivery_type": Order.DELIVERY_PICKUP,
            "payment_method": Order.PAYMENT_COD,
        }
        data.update(overrides)
        return data

    def _post_checkout(self, data):
        with (
            patch("apps.orders.tasks.send_order_confirmation.delay"),
            patch("apps.orders.tasks.send_admin_order_notification.delay"),
        ):
            return self.client.post(
                "/basket/",
                data,
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

    def test_public_pages_render_when_social_apps_are_not_configured(self):
        SocialApp.objects.all().delete()

        for path in ("/basket/", "/login", "/register"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)
                self.assertEqual(response.status_code, 200)

    def test_existing_credentials_do_not_create_duplicate_and_valid_password_attaches_order(self):
        existing = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self._anonymous_cart()

        response = self._post_checkout(
            self._checkout_data(
                register_account="on",
                reg_password="Strongpass1",
                reg_password2="Strongpass1",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="buyer@example.com").count(), 1)
        self.assertEqual(Order.objects.get().user, existing)
        self.assertEqual(get_user(self.client).pk, existing.pk)

    def test_existing_credentials_with_wrong_password_do_not_create_order(self):
        User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self._anonymous_cart()

        response = self._post_checkout(
            self._checkout_data(
                register_account="on",
                reg_password="Otherpass2",
                reg_password2="Otherpass2",
            )
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact="buyer@example.com").count(), 1)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_registered_email_without_login_flag_does_not_create_guest_order(self):
        User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self._anonymous_cart()

        response = self._post_checkout(self._checkout_data())

        self.assertEqual(response.status_code, 400)
        self.assertIn("уже существует", response.json()["error"])
        self.assertFalse(Order.objects.exists())
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_account_status_detects_existing_account_before_checkout(self):
        User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )

        response = self.client.post(
            "/basket/account-status/",
            {"email": "BUYER@example.com", "phone": "+7 (999) 111-22-33"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": True,
                "conflict": False,
                "has_phone": True,
                "password_login_available": True,
            },
        )

    def test_existing_account_phone_is_reused_when_guest_phone_is_hidden(self):
        existing = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            phone_confirmed=True,
            password="Strongpass1",
        )
        self._anonymous_cart()

        response = self._post_checkout(
            self._checkout_data(
                phone="",
                register_account="on",
                reg_password="Strongpass1",
                reg_password2="Strongpass1",
            )
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        self.assertEqual(order.user, existing)
        self.assertEqual(order.contact_phone, "+79991112233")
        self.assertEqual(
            User.objects.filter(phone="+79991112233").count(),
            1,
        )

    def test_guest_checkout_hides_duplicate_phone_for_existing_account(self):
        User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            phone_confirmed=True,
            password="Strongpass1",
        )
        self._anonymous_cart()

        response = self.client.get("/basket/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'existingAccountHasPhone: false')
        self.assertContains(response, 'x-show="!existingAccountHasPhone"')
        self.assertContains(
            response,
            "Телефон будет использован из найденной учётной записи после входа.",
        )

    def test_guest_sees_address_fields_without_new_address_controls(self):
        self._anonymous_cart()
        site = Site.objects.get_current()
        for provider in ("yandex", "vk"):
            app = SocialApp.objects.create(
                provider=provider,
                name=provider,
                client_id=f"{provider}-test-client",
                secret="test-secret",
            )
            app.sites.add(site)

        response = self.client.get("/basket/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="city"')
        self.assertContains(response, 'name="street"')
        self.assertContains(response, 'name="house"')
        self.assertNotContains(response, "Новый адрес")
        self.assertNotContains(response, "Сделать основным адресом")

    def test_disabled_delivery_method_is_rejected_server_side(self):
        self.site_settings.enable_pickup = False
        self.site_settings.save(update_fields=["enable_pickup"])
        self._anonymous_cart()

        response = self._post_checkout(self._checkout_data())

        self.assertEqual(response.status_code, 400)
        self.assertIn("недоступен", response.json()["error"])
        self.assertFalse(Order.objects.exists())

    def test_internal_balance_below_order_total_is_rejected_server_side(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
            balance=Decimal("100.00"),
        )
        self.client.force_login(user)
        self._user_cart(user)

        response = self._post_checkout(
            self._checkout_data(payment_method=Order.PAYMENT_INTERNAL)
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Недостаточно средств", response.json()["error"])
        self.assertFalse(Order.objects.exists())
        user.refresh_from_db()
        self.assertEqual(user.balance, Decimal("100.00"))

    def test_saved_addresses_keep_new_address_fields_collapsed(self):
        user = User.objects.create_user(
            email="address@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        Address.objects.create(
            user=user,
            city="Москва",
            street="Новая",
            house="1",
            postal_code="123456",
            is_default=True,
        )
        self.client.force_login(user)
        self._user_cart(user)
        site = Site.objects.get_current()
        for provider in ("yandex", "vk"):
            app = SocialApp.objects.create(
                provider=provider,
                name=provider,
                client_id=f"{provider}-address-test-client",
                secret="test-secret",
            )
            app.sites.add(site)

        response = self.client.get("/basket/")

        self.assertContains(response, 'x-show="showNewAddress || !hasAddresses"')
        self.assertNotContains(response, 'showNewAddress || !selectedAddressId || !hasAddresses')
        self.assertContains(response, "newAddressIsDefault ? 'Основной адрес' : 'Сделать основным адресом'")

    def test_default_checkout_delivery_is_cdek_when_own_methods_are_disabled(self):
        self.site_settings.enable_pickup = False
        self.site_settings.enable_city_courier = False
        self.site_settings.enable_cdek_pvz = True
        self.site_settings.enable_cdek_door = True
        self.site_settings.save()
        self._anonymous_cart()
        site = Site.objects.get_current()
        for provider in ("yandex", "vk"):
            app = SocialApp.objects.create(
                provider=provider,
                name=provider,
                client_id=f"{provider}-test-client",
                secret="test-secret",
            )
            app.sites.add(site)

        response = self.client.get("/basket/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["default_delivery_type"], Order.DELIVERY_CDEK_PVZ)
        self.assertContains(response, '.delivery-options label:has(input[value="courier"]) { display: none; }')
        self.assertContains(response, '.delivery-options label:has(input[value="pickup"]) { display: none; }')

    def test_new_registration_creates_user_and_attaches_order(self):
        self._anonymous_cart()

        response = self._post_checkout(
            self._checkout_data(
                register_account="on",
                reg_password="Strongpass1",
                reg_password2="Strongpass1",
            )
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="buyer@example.com")
        self.assertEqual(Order.objects.get().user, user)
        self.assertEqual(get_user(self.client).pk, user.pk)

    @patch(
        "apps.delivery.cdek.CDEKClient.calc_delivery_cost",
        return_value={
            "cost": Decimal("790.00"),
            "period_min": 2,
            "period_max": 3,
            "tariff_name": "Склад-дверь",
        },
    )
    def test_cdek_door_uses_cdek_address_for_order_and_main_profile_address(self, calc_mock):
        user = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self.client.force_login(user)
        self._user_cart(user)

        response = self._post_checkout(
            self._checkout_data(
                city="Старая форма",
                street="Старая улица",
                house="1",
                apartment="2",
                postal_code="000000",
                cdek_city_code="44",
                cdek_city_name="Москва, Москва",
                cdek_street="Арбат",
                cdek_house="10",
                cdek_apartment="15",
                cdek_postal_code="119002",
                cdek_delivery_cost="1",
                delivery_type=Order.DELIVERY_CDEK_DOOR,
                is_address_main="on",
            )
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        self.assertEqual(
            order.delivery_address,
            {
                "city": "Москва, Москва",
                "street": "Арбат",
                "house": "10",
                "apartment": "15",
                "postal_code": "119002",
            },
        )
        self.assertEqual(order.delivery_cost, Decimal("790.00"))
        self.assertEqual(order.total_amount, Decimal("1290.00"))
        address = Address.objects.get(user=user)
        self.assertEqual(address.city, "Москва, Москва")
        self.assertEqual(address.street, "Арбат")
        self.assertEqual(address.house, "10")
        self.assertEqual(address.apartment, "15")
        self.assertEqual(address.postal_code, "119002")
        self.assertTrue(address.is_default)
        calc_mock.assert_called_once_with(
            to_city_code=44,
            weight_grams=250,
            delivery_type=Order.DELIVERY_CDEK_DOOR,
            to_address="Арбат, д. 10",
            to_postal_code="119002",
        )

    def test_other_recipient_is_validated_normalized_and_saved(self):
        self._anonymous_cart()

        response = self._post_checkout(
            self._checkout_data(
                other_recipient="on",
                recipient_name="Петр Петров",
                recipient_phone_code="+7",
                recipient_phone="(999) 555-44-33",
            )
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        self.assertEqual(order.recipient_name, "Петр Петров")
        self.assertEqual(order.recipient_phone, "+79995554433")
        self.assertEqual(order.delivery_recipient_name, "Петр Петров")
        self.assertEqual(order.delivery_recipient_phone, "+79995554433")

    @override_settings(YOOKASSA_SHOP_ID="", YOOKASSA_SECRET_KEY="")
    def test_card_checkout_creates_pending_recurring_plan(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self.client.force_login(user)
        self._user_cart(user)

        response = self._post_checkout(self._checkout_data(
            payment_method=Order.PAYMENT_CARD,
            repeat_order="on",
            repeat_weeks="3",
        ))

        self.assertEqual(response.status_code, 200)
        plan = RecurringOrder.objects.get()
        self.assertEqual(plan.source_order.user, user)
        self.assertEqual(plan.interval_weeks, 3)
        self.assertEqual(plan.status, RecurringOrder.STATUS_PENDING)

    def test_recurring_plan_rejects_non_card_payment(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            phone="+79991112233",
            password="Strongpass1",
        )
        self.client.force_login(user)
        self._user_cart(user)

        response = self._post_checkout(self._checkout_data(
            payment_method=Order.PAYMENT_COD,
            repeat_order="on",
        ))

        self.assertEqual(response.status_code, 400)
        self.assertIn("только при оплате картой", response.json()["error"])
        self.assertFalse(Order.objects.exists())
