from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ProfileMobileLayoutTests(SimpleTestCase):
    def test_active_account_tab_and_address_tiles_have_mobile_contracts(self):
        base_account = (
            Path(settings.BASE_DIR) / "apps/users/templates/users/base_account.html"
        ).read_text(encoding="utf-8")
        profile = (
            Path(settings.BASE_DIR) / "apps/users/templates/users/profile.html"
        ).read_text(encoding="utf-8")

        self.assertIn("line-height: 19px !important", base_account)
        self.assertIn("account-balance-summary", base_account)
        self.assertIn("height: 34px !important", base_account)
        self.assertIn(".account-heading-row > h1", base_account)
        self.assertIn("display: none !important", base_account)
        self.assertIn("revealCurrentAccountTab", base_account)
        self.assertIn("nav.scrollTo", base_account)
        self.assertIn("asp-addr", profile)
        self.assertIn("@media", profile)
        self.assertIn('name="street"', profile)
        self.assertIn('name="house"', profile)
        self.assertIn("address.house", profile)
