from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TransactionTestCase


class MigrationStateTests(SimpleTestCase):
    def test_complete_historical_state_renders_without_dangling_model_references(self):
        state = MigrationLoader(None).project_state()
        for model in state.apps.get_models():
            list(model._meta.get_fields())


class ContactEmailUpgradeTests(TransactionTestCase):
    def test_existing_site_settings_survive_upgrade_from_previous_release(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("catalog", "0047_clear_accessory_taste_defaults")])
            old_apps = executor.loader.project_state([("catalog", "0047_clear_accessory_taste_defaults")]).apps
            site = old_apps.get_model("catalog", "SiteSettings").objects.get_or_create(pk=1)[0]
            site.site_name = "Existing customer content"
            site.save()
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            new_apps = executor.loader.project_state(latest).apps
            site = new_apps.get_model("catalog", "SiteSettings").objects.get(pk=1)
            self.assertEqual(site.site_name, "Existing customer content")
            self.assertEqual(site.contact_email, "aspectcoffeeroasters@gmail.com")
        finally:
            MigrationExecutor(connection).migrate(latest)
