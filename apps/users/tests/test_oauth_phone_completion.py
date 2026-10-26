from allauth.socialaccount.models import SocialAccount
from django.test import TestCase
from django.urls import reverse

from apps.users.adapters import CustomSocialAccountAdapter
from apps.users.models import User


class OAuthPhoneCompletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="oauth-user@example.com",
            password=None,
        )
        SocialAccount.objects.create(
            user=self.user,
            provider="yandex",
            uid="oauth-user-1",
            extra_data={},
        )
        self.client.force_login(self.user)

    def test_oauth_user_without_phone_is_redirected_to_completion(self):
        response = self.client.get("/basket/")

        self.assertRedirects(
            response,
            reverse("users:complete_phone"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session["phone_completion_next"],
            "/basket/",
        )

    def test_completion_explains_missing_oauth_phone(self):
        response = self.client.get(reverse("users:complete_phone"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "не передал его при входе",
        )
        self.assertContains(response, "Яндекс")

    def test_completion_requires_matching_phone_confirmation(self):
        response = self.client.post(
            reverse("users:complete_phone"),
            {
                "phone_code": "+7",
                "phone": "9991112233",
                "phone_repeat": "9991112244",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Номера не совпадают")
        self.user.refresh_from_db()
        self.assertFalse(self.user.phone_confirmed)
        self.assertEqual(self.user.phone, "")

    def test_completion_rejects_phone_owned_by_another_account(self):
        User.objects.create_user(
            email="owner@example.com",
            phone="+79991112233",
            phone_confirmed=True,
        )

        response = self.client.post(
            reverse("users:complete_phone"),
            {
                "phone_code": "+7",
                "phone": "9991112233",
                "phone_repeat": "9991112233",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже используется другим аккаунтом")
        self.user.refresh_from_db()
        self.assertFalse(self.user.phone_confirmed)

    def test_completion_saves_phone_and_returns_to_original_page(self):
        session = self.client.session
        session["phone_completion_next"] = "/basket/?from=oauth"
        session.save()

        response = self.client.post(
            reverse("users:complete_phone"),
            {
                "phone_code": "+7",
                "phone": "9991112233",
                "phone_repeat": "9991112233",
            },
        )

        self.assertRedirects(
            response,
            "/basket/?from=oauth",
            fetch_redirect_response=False,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+79991112233")
        self.assertTrue(self.user.phone_confirmed)

    def test_provider_phone_is_saved_as_confirmed(self):
        adapter = CustomSocialAccountAdapter()

        adapter._sync_social_phone(
            self.user,
            "yandex",
            {"default_phone": {"number": "+79995556677"}},
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+79995556677")
        self.assertTrue(self.user.phone_confirmed)

        response = self.client.get("/basket/")
        self.assertNotEqual(response.status_code, 302)
