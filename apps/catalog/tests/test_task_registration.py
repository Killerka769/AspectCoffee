import ast
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class CatalogTaskRegistrationTests(SimpleTestCase):
    def test_commented_tasks_do_not_decorate_the_next_live_function(self):
        source = Path(__file__).parents[1] / 'tasks.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = [value.func if isinstance(value, ast.Call) else value
                          for value in node.decorator_list]
            count = sum(isinstance(value, ast.Name) and value.id == 'shared_task'
                        for value in decorators)
            self.assertLessEqual(count, 1, node.name)

    def test_fresh_processes_finalize_tasks_with_different_hash_seeds(self):
        root = Path(__file__).parents[3]
        probe = '''
import django
django.setup()
from config.celery import app
app.loader.import_default_modules()
app.finalize()
for name in ('send_admin_new_review_notification', 'check_product_images'):
    full_name = 'apps.catalog.tasks.' + name
    assert app.tasks[full_name].name == full_name
print('REGISTRY_OK')
'''
        for seed in ('1', '2', '3', '4'):
            with self.subTest(seed=seed):
                env = os.environ | {
                    'PYTHONHASHSEED': seed,
                    'PYTHONDONTWRITEBYTECODE': '1',
                    'DJANGO_SETTINGS_MODULE': 'config.settings.test',
                }
                result = subprocess.run([sys.executable, '-c', probe], cwd=root,
                                        env=env, capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stderr[-1200:])
                self.assertIn('REGISTRY_OK', result.stdout)
