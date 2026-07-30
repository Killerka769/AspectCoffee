from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEGACY_ASCII = bytes.fromhex("7461737479").decode("ascii")
LEGACY_RUSSIAN = (
    "\u0442\u0435\u0439\u0441\u0442\u0438",
    "\u0442\u044d\u0439\u0441\u0442\u0438",
)
ALLOWED_SOURCE_FILES = {
    "apps/catalog/management/commands/check_images.py",
    "apps/catalog/management/commands/run_parser.py",
    "docs/05_MAIL_PARSER_AND_JOBS.md",
    "templates/admin/catalog/parsersetting/run_parser.html",
}
IGNORED_DIRS = {
    ".git",
    ".venv",
    ".work",
    "__pycache__",
    "media",
    "node_modules",
    "runtime",
    "staticfiles",
    "venv",
}
TEXT_SUFFIXES = {
    ".conf",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


class LegacyBrandGuardTests(SimpleTestCase):
    def test_legacy_brand_is_confined_to_parser_integration(self):
        violations = []
        for path in PROJECT_ROOT.rglob("*"):
            relative = path.relative_to(PROJECT_ROOT)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue

            relative_name = relative.as_posix()
            lowered_name = relative_name.casefold()
            if path.is_dir():
                if LEGACY_ASCII in lowered_name or any(token in lowered_name for token in LEGACY_RUSSIAN):
                    violations.append(f"имя каталога: {relative_name}")
                continue

            if LEGACY_ASCII in lowered_name or any(token in lowered_name for token in LEGACY_RUSSIAN):
                violations.append(f"имя файла: {relative_name}")

            if relative_name in ALLOWED_SOURCE_FILES:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile", ".gitignore"}:
                continue

            content = path.read_text(encoding="utf-8", errors="ignore").casefold()
            if LEGACY_ASCII in content or any(token in content for token in LEGACY_RUSSIAN):
                violations.append(f"содержимое: {relative_name}")

        self.assertEqual([], violations, "Запрещённое наследие бренда найдено:\n" + "\n".join(violations))

    def test_production_image_uses_aspectcoffee_name(self):
        compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("image: aspectcoffee-web", compose)
        self.assertNotIn(LEGACY_ASCII, compose.casefold())
