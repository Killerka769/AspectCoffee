import os
import logging
import httpx
from urllib.parse import urljoin
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from apps.catalog.models import Product

logger = logging.getLogger(__name__)
BASE_URL = "https://shop.tastycoffee.ru"


class Command(BaseCommand):
    help = "Check all products for missing image files and re-download from source"

    def add_arguments(self, parser):
        parser.add_argument("--fix", action="store_true", default=False,
                            help="Actually re-download missing images (dry-run by default)")

    def handle(self, *args, **options):
        fix = options["fix"]
        products = Product.objects.exclude(main_image='').exclude(main_image__isnull=True)
        missing = []
        for p in products:
            try:
                if not os.path.exists(p.main_image.path):
                    missing.append(p)
            except Exception:
                missing.append(p)

        if not missing:
            self.stdout.write(self.style.SUCCESS(f"All {products.count()} product images are present on disk."))
            return

        self.stdout.write(f"Found {len(missing)} products with missing image files.")
        if not fix:
            self.stdout.write("Dry-run mode. Use --fix to re-download.")
            for p in missing:
                self.stdout.write(f"  MISSING: {p.slug} -> {p.main_image.name}")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        fixed = 0
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for p in missing:
                try:
                    # Re-run parser for this specific product to get image URL
                    slug_path = f"coffee/{p.slug}"
                    url = f"{BASE_URL}/{slug_path}"
                    resp = client.get(url)
                    if resp.status_code != 200:
                        self.stdout.write(f"  SKIP (HTTP {resp.status_code}): {p.slug}")
                        continue

                    import json, re
                    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
                    if not m:
                        self.stdout.write(f"  SKIP (no NUXT): {p.slug}")
                        continue
                    p_data = json.loads(m.group(1))

                    # Find image URL
                    def resolve(val, data):
                        seen = set()
                        curr = val
                        while type(curr) is int and 0 <= curr < len(data):
                            if curr in seen: break
                            seen.add(curr)
                            curr = data[curr]
                        return curr

                    def resolve_image(val, data):
                        r = resolve(val, data)
                        if isinstance(r, str) and len(r) > 3: return r
                        if isinstance(r, dict):
                            for k in ("original", "path", "url", "src", "webp", "jpeg"):
                                v = r.get(k)
                                if v is not None:
                                    rv = resolve(v, data)
                                    if isinstance(rv, str) and len(rv) > 3: return rv
                        if isinstance(r, list) and len(r) > 0:
                            return resolve_image(r[0], data)
                        return None

                    i_url = None
                    for idx in range(len(p_data)):
                        val = resolve(idx, p_data)
                        if isinstance(val, dict) and "slug" in val:
                            ns = resolve(val.get("slug"), p_data)
                            if isinstance(ns, str) and ns.strip('/').split('/')[-1] == p.slug:
                                # Found node
                                img = val.get("image")
                                if img: i_url = resolve_image(img, p_data)
                                if not i_url:
                                    imgs = val.get("images")
                                    if imgs:
                                        imgs_r = resolve(imgs, p_data)
                                        if isinstance(imgs_r, list):
                                            for ref in imgs_r:
                                                c = resolve_image(ref, p_data)
                                                if c: i_url = c; break
                                break

                    if not i_url:
                        self.stdout.write(f"  NO URL: {p.slug}")
                        continue

                    full_url = urljoin(BASE_URL, str(i_url))
                    img_resp = client.get(full_url, timeout=15.0)
                    if img_resp.status_code == 200:
                        ext = str(i_url).rsplit('.', 1)[-1].split('?')[0].lower()
                        if ext not in ["jpg", "jpeg", "png", "webp"]: ext = "webp"
                        fname = f"{p.slug}.{ext}"
                        p.main_image.save(fname, ContentFile(img_resp.content), save=True)
                        fixed += 1
                        self.stdout.write(self.style.SUCCESS(f"  FIXED: {p.slug}"))
                    else:
                        self.stdout.write(f"  IMG HTTP {img_resp.status_code}: {p.slug}")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ERROR: {p.slug}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone. Fixed {fixed}/{len(missing)} images."))
