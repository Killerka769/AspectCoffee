from django.apps import apps
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse


class RetiredAchievementFeatureTests(SimpleTestCase):
    def test_removed_models_are_not_reintroduced_by_handover_merge(self):
        labels = {model._meta.label_lower for model in apps.get_models()}
        for label in ("users.achievement", "users.userachievement", "users.discountlevel"):
            self.assertNotIn(label, labels)

    def test_removed_achievement_and_history_routes_stay_removed(self):
        for name in ("users:achievements", "users:blog_history"):
            with self.assertRaises(NoReverseMatch):
                reverse(name)
