import json
import logging
import re
import time
import traceback
from decimal import Decimal
from urllib.parse import urljoin
from html import unescape

import httpx
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify as django_slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://shop.tastycoffee.ru"

LEGACY_BRAND_REPLACEMENTS = (
    ("TASTY COFFEE", "ASPECT COFFEE"),
    ("Tasty Coffee", "Aspect Coffee"),
    ("tasty coffee", "aspect coffee"),
    ("tasty-coffee", "aspectcoffee"),
    ("tastycoffee", "aspectcoffee"),
    ("Тейсти Кофе", "Aspect Coffee"),
    ("Тэйсти Кофе", "Aspect Coffee"),
    ("TASTY", "ASPECT"),
    ("Tasty", "Aspect"),
    ("tasty", "aspect"),
    ("ТЕЙСТИ", "ASPECT"),
    ("Тейсти", "Aspect"),
    ("тейсти", "aspect"),
    ("ТЭЙСТИ", "ASPECT"),
    ("Тэйсти", "Aspect"),
    ("тэйсти", "aspect"),
)
LEGACY_BRAND_MARKERS = ("tasty", "тейсти", "тэйсти")


def replace_source_brand(value):
    """Replace source branding in plain text before it reaches public models."""
    result = str(value or "")
    for source, replacement in LEGACY_BRAND_REPLACEMENTS:
        result = result.replace(source, replacement)
    return result


def sanitize_imported_html(value):
    """Remove source-branded remote media/links and normalize visible text."""
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "html.parser")
    for tag in list(soup.find_all(True)):
        remove_media = False
        for attribute, raw_value in list(tag.attrs.items()):
            attribute_value = " ".join(raw_value) if isinstance(raw_value, list) else str(raw_value)
            if not any(marker in attribute_value.casefold() for marker in LEGACY_BRAND_MARKERS):
                continue
            if tag.name in {"audio", "iframe", "img", "source", "video"}:
                tag.decompose()
                remove_media = True
                break
            del tag.attrs[attribute]
        if remove_media:
            continue

    for empty_picture in list(soup.find_all("picture")):
        if not empty_picture.find(True) and not empty_picture.get_text(strip=True):
            empty_picture.decompose()

    return replace_source_brand(str(soup))

def slugify_ru(text: str) -> str:
    tr = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
        "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
        "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
    result = []
    for ch in text.lower(): result.append(tr.get(ch, ch))
    return django_slugify("".join(result))

def clean_decimal(val, max_digits=10, decimal_places=2):
    if val is None: return None
    try:
        s = str(val).replace('%', '').replace(',', '.').strip()
        if not s or s.lower() == 'none' or s == '""' or s == "''": return None
        d = Decimal(s)
        limit = Decimal('10') ** (max_digits - decimal_places) - (Decimal('1') / (Decimal('10') ** decimal_places))
        if d > limit: d = limit
        if d < -limit: d = -limit
        return d.quantize(Decimal('1.' + '0' * decimal_places))
    except:
        return None

def resolve_nuxt(val, data):
    seen = set()
    curr = val
    while type(curr) is int and 0 <= curr < len(data):
        if curr in seen: break
        seen.add(curr)
        curr = data[curr]
    return curr

def to_int(v, default=0):
    if v is None: return default
    if isinstance(v, (int, float)): return int(v)
    try:
        s = str(v).strip()
        if not s: return default
        return int(float(s.replace(',', '.')))
    except:
        return default

def resolve_image_url(val, data):
    """Recursively resolve a NUXT value into an image URL string."""
    if val is None:
        return None
    resolved = resolve_nuxt(val, data)
    if isinstance(resolved, str) and len(resolved) > 3:
        return resolved
    if isinstance(resolved, dict):
        for key in ("original", "path", "url", "src", "webp", "jpeg", "jpg"):
            v = resolved.get(key)
            if v is not None:
                r = resolve_nuxt(v, data)
                if isinstance(r, str) and len(r) > 3:
                    return r
    if isinstance(resolved, list) and len(resolved) > 0:
        return resolve_image_url(resolved[0], data)
    return None

def extract_price_from_data(p_data):
    """
    Brute-force scan the entire flat NUXT array to find a reasonable price value.
    Returns Decimal or 0.
    """
    best = Decimal("0")

    # Pass 1: look for any dict with price-like keys
    for x in p_data:
        if not isinstance(x, dict):
            continue

        for price_key in ("price", "price_value", "price_with_discount", "price_without_discount", "base_price", "min_price", "current_price"):
            raw = x.get(price_key)
            if raw is None:
                continue

            pr = resolve_nuxt(raw, p_data)

            # Sometimes NUXT data has strings for numbers
            if isinstance(pr, str):
                try:
                    pr = float(pr.replace(',', '.').strip())
                except:
                    continue

            if isinstance(pr, (int, float)) and 100 < pr < 100000:
                d = clean_decimal(pr, 10, 2)
                if not d: continue

                # If we find a dict that has both 'title' or 'weight' AND 'price', check if it's 250
                weight_val = None
                for wk in ("weight", "title", "name", "value"):
                    w_raw = x.get(wk)
                    if w_raw is not None:
                        w_res = resolve_nuxt(w_raw, p_data)
                        if isinstance(w_res, (str, int, float)) and "250" in str(w_res):
                            return d # FOUND EXACTLY 250g price

                if d > best:
                    best = d

    return best

class Command(BaseCommand):
    help = "ULTIMATE Parser v16 - Fixed price & image extraction."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--category", type=str, default="coffee")
        parser.add_argument("--update-images", action="store_true", default=False,
                            help="Force re-download images even for existing products")

    def handle(self, *args, **options):
        self.limit = options["limit"]
        self.category_filter = options["category"]
        self.update_images = options.get("update_images", False)

        from apps.catalog.models import Product, Category, ProductVariant, FlavorNote, ProductImage
        from django.utils import timezone

        # log = ParserLog.objects.create(status="running")
        total_created = 0
        total_updated = 0
        total_found = 0
        client = None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }

            client = httpx.Client(timeout=40.0, follow_redirects=True, headers=headers)
            page = 1
            total_handled = 0

            while True:
                cat_url = f"{BASE_URL}/{self.category_filter}?page={page}"
                self.stdout.write(f"Fetching catalog page {page}: {cat_url}")
                try:
                    resp = client.get(cat_url)
                    if resp.status_code != 200:
                        self.stdout.write(f"  HTTP {resp.status_code} — stop.")
                        break
                except Exception as e:
                    self.stdout.write(f"  Error: {e} — stop.")
                    break

                data = self._extract_nuxt(resp.text)
                if not data:
                    self.stdout.write("  No NUXT data found — stop.")
                    break

                product_slugs = []
                allowed_prefixes = ("/coffee/", "/tea/", "/accessories/", "/chocolate/", "/giftbox/")
                for idx in range(len(data)):
                    item = resolve_nuxt(idx, data)
                    if isinstance(item, dict) and "slug" in item:
                        s = resolve_nuxt(item.get("slug"), data)
                        if isinstance(s, str) and any(s.startswith(p) for p in allowed_prefixes):
                           product_slugs.append(s.strip('/'))

                product_slugs = list(dict.fromkeys(product_slugs))
                if not product_slugs:
                    self.stdout.write("  No product slugs found — stop.")
                    break

                self.stdout.write(f"  Found {len(product_slugs)} products on page {page}.")

                for slug_path in product_slugs:
                    if self.limit and total_handled >= self.limit: return

                    full_p_url = urljoin(BASE_URL, f"/{slug_path}")
                    slug = slug_path.split('/')[-1]

                    try:
                        self.stdout.write(f"  Parsing: {slug}...")
                        p_resp = client.get(full_p_url)
                        if p_resp.status_code != 200:
                            self.stdout.write(f"    HTTP {p_resp.status_code} — skip.")
                            continue

                        p_data = self._extract_nuxt(p_resp.text)
                        if not p_data:
                            self.stdout.write(f"    No NUXT data — skip.")
                            continue

                        # Find product node: must have name+slug and price OR additional_info
                        node = None
                        for x_idx in range(len(p_data)):
                            val = resolve_nuxt(x_idx, p_data)
                            if isinstance(val, dict) and "name" in val and "slug" in val:
                                ns = resolve_nuxt(val.get("slug"), p_data)
                                if isinstance(ns, str) and ns.strip('/').split('/')[-1] == slug:
                                    node = val
                                    break

                        if not node:
                            self.stdout.write(f"    SKIPPED: node not found for {slug}")
                            continue

                        def get_p(key, default=""):
                            if not isinstance(node, dict): return default
                            v = node.get(key)
                            if v is None: return default
                            return resolve_nuxt(v, p_data)

                        name = replace_source_brand(get_p("name"))
                        if not name:
                            self.stdout.write(f"    SKIPPED: no name for {slug}")
                            continue

                        slug = replace_source_brand(slug)
                        full_desc = sanitize_imported_html(get_p("description") or get_p("mini_description") or "")
                        mini_desc = sanitize_imported_html(get_p("mini_description") or "")
                        flavor_html = sanitize_imported_html(get_p("flavor_description") or "")

                        altitude = ""; region = ""; proc = ""; q = None; caffeine = None; variety = ""
                        additional_info = get_p("additional_info", [])
                        if isinstance(additional_info, list):
                            for idx in additional_info:
                                info = resolve_nuxt(idx, p_data)
                                if isinstance(info, dict):
                                    k = resolve_nuxt(info.get("key"), p_data)
                                    v = resolve_nuxt(info.get("value"), p_data)
                                    if k == "growing_height": altitude = str(v)
                                    elif k == "region": region = str(v)
                                    elif k in ("processing", "processing_method"): proc = str(v)
                                    elif k == "caffeine": caffeine = clean_decimal(v, 4, 2)
                                    elif k == "q_grader_grade": q = clean_decimal(v, 4, 2)
                                    elif k == "variety": variety = str(v)

                        brand_node = node.get("brand")
                        c_name = "Кофе"
                        if self.category_filter == "tea": c_name = "Чай"
                        elif self.category_filter == "accessories": c_name = "Аксессуары"

                        if brand_node:
                            brand = resolve_nuxt(brand_node, p_data)
                            if isinstance(brand, dict):
                                b_name = resolve_nuxt(brand.get("name"), p_data)
                                if b_name: c_name = b_name

                        category, _ = Category.objects.get_or_create(slug=slugify_ru(c_name), defaults={"name": c_name})

                        body = to_int(get_p("saturation", get_p("body", 5)), 5)
                        acidity = to_int(get_p("sourness", get_p("acidity", 5)), 5)
                        used_for = str(get_p("used_for", "filter")).lower()
                        roast = "espresso" if "espresso" in used_for or "espresso" in name.lower() else "medium"

                        is_featured = get_p("week_special", False)
                        is_new = False
                        is_bestseller = False

                        s_flags = get_p("special_flags", [])
                        if isinstance(s_flags, list):
                            for sf_idx in s_flags:
                                sf = resolve_nuxt(sf_idx, p_data)
                                if isinstance(sf, dict):
                                    sf_id = to_int(resolve_nuxt(sf.get("id"), p_data))
                                    if sf_id == 32: is_new = True
                                    elif sf_id == 31: is_bestseller = True

                        product, created = Product.objects.update_or_create(
                            slug=slug,
                            defaults={
                                "name": name, "category": category, "description": full_desc,
                                "short_description": mini_desc,
                                "roast_level": roast,
                                "processing_method": proc, "altitude": altitude, "region": region,
                                "caffeine_content": caffeine, "variety": variety,
                                "body": min(10, max(0, body)),
                                "acidity": min(10, max(0, acidity)),
                                "sweetness": min(10, max(0, to_int(get_p("sweetness", 5), 5))),
                                "flavor_description_html": flavor_html,
                                "is_active": True, "in_stock": True,
                                "is_featured": is_featured,
                                "is_new": is_new,
                                "is_bestseller": is_bestseller,
                            }
                        )

                        if q is not None and not product.q_score:
                            product.q_score = str(q).replace('.', ',') + '+'
                            product.save(update_fields=['q_score'])

                        # ── IMAGE EXTRACTION ──────────────────────────────────────────────
                        i_url = None

                        # 1. node["image"] field (can be str, dict, or int ref)
                        img_field = node.get("image")
                        if img_field is not None:
                            i_url = resolve_image_url(img_field, p_data)

                        # 2. node["images"] list
                        if not i_url:
                            imgs_field = node.get("images")
                            if imgs_field is not None:
                                imgs_resolved = resolve_nuxt(imgs_field, p_data)
                                if isinstance(imgs_resolved, list):
                                    for img_ref in imgs_resolved:
                                        candidate = resolve_image_url(img_ref, p_data)
                                        if candidate:
                                            i_url = candidate
                                            break

                        # 3. mockup_image / preview
                        if not i_url:
                            for key in ("mockup_image", "preview", "preview_image", "thumbnail"):
                                v = node.get(key)
                                if v is not None:
                                    candidate = resolve_image_url(v, p_data)
                                    if candidate:
                                        i_url = candidate
                                        break

                        # 4. brute-force scan: find any dict with "original" or "path" key
                        if not i_url:
                            for x in p_data:
                                if isinstance(x, dict):
                                    for key in ("original", "path"):
                                        v = x.get(key)
                                        if isinstance(v, str) and (
                                            slug in v or
                                            any(ext in v for ext in [".jpg", ".jpeg", ".png", ".webp"])
                                        ):
                                            i_url = v
                                            break
                                if i_url:
                                    break

                        should_download = i_url and (created or not product.main_image or self.update_images)
                        if should_download:
                            full_i_url = urljoin(BASE_URL, str(i_url))
                            try:
                                img_r = client.get(full_i_url, timeout=15.0)
                                if img_r.status_code == 200:
                                    ext = str(i_url).rsplit('.', 1)[-1].split('?')[0].lower()
                                    if ext not in ["jpg", "jpeg", "png", "webp"]: ext = "webp"
                                    fname = f"{slug}.{ext}"
                                    product.main_image.save(fname, ContentFile(img_r.content), save=True)
                                    self.stdout.write(self.style.SUCCESS(f"    IMAGE OK → {fname}"))
                                else:
                                    self.stdout.write(f"    Image HTTP {img_r.status_code} for {full_i_url}")
                            except Exception as img_ex:
                                self.stdout.write(f"    Image error: {img_ex}")
                        elif not i_url:
                            self.stdout.write(f"    No image URL found for {slug}")

                        # ── PRICE & VARIANT EXTRACTION ──────────────────────────────────────────────
                        variants_to_create = {} # weight -> price

                        # Strategy 1: measurable_option → values list
                        mo_raw = node.get("measurable_option")
                        if mo_raw is not None:
                            mo = resolve_nuxt(mo_raw, p_data)
                            if isinstance(mo, dict):
                                vals_raw = mo.get("values")
                                if vals_raw is not None:
                                    vals = resolve_nuxt(vals_raw, p_data)
                                    if isinstance(vals, list):
                                        for item_ref in vals:
                                            item_d = resolve_nuxt(item_ref, p_data)
                                            if not isinstance(item_d, dict): continue

                                            t_raw = item_d.get("title")
                                            t = str(resolve_nuxt(t_raw, p_data) or "").lower()

                                            weight = 250
                                            if "1000" in t or "1кг" in t or "1 кг" in t: weight = 1000
                                            elif "250" in t: weight = 250
                                            else: continue # Skip unknown weights for now

                                            for price_key in ("price", "price_without_discount", "base_price"):
                                                pr_raw = item_d.get(price_key)
                                                if pr_raw is None: continue
                                                pr = resolve_nuxt(pr_raw, p_data)
                                                if isinstance(pr, (int, float)) and pr > 0:
                                                    d = clean_decimal(pr, 10, 2)
                                                    if d:
                                                        variants_to_create[weight] = d
                                                        break

                        # Strategy 2: Fallback if no measurable_option
                        if not variants_to_create:
                            v_price = Decimal("0")
                            for price_key in ("price", "price_without_discount", "base_price"):
                                pr_raw = node.get(price_key)
                                if pr_raw is not None:
                                    pr = resolve_nuxt(pr_raw, p_data)
                                    if isinstance(pr, (int, float)) and 50 < pr < 50000:
                                        d = clean_decimal(pr, 10, 2)
                                        if d:
                                            v_price = d
                                            break
                            if v_price == 0:
                                v_price = extract_price_from_data(p_data)

                            if v_price > 0:
                                variants_to_create[250] = v_price

                        if not variants_to_create:
                            variants_to_create[250] = Decimal("750") # ultra fallback

                        # Ensure both 250 and 1000 variants exist if product is coffee/tea (not drip/capsule)
                        is_small_format = any(k in slug for k in ("drip", "capsule", "instant", "cola", "cold_coffee"))
                        if not is_small_format:
                            if 250 in variants_to_create and 1000 not in variants_to_create:
                                # 1000g is typically ~3x of 250g price (with bulk discount)
                                variants_to_create[1000] = (variants_to_create[250] * Decimal("3")).quantize(Decimal("1.00"))
                            elif 1000 in variants_to_create and 250 not in variants_to_create:
                                # 250g is typically ~1/3 of 1000g price
                                variants_to_create[250] = (variants_to_create[1000] / Decimal("3")).quantize(Decimal("1.00"))

                        # Create packaging (price) + variant (grind/roast) in DB (1.7)
                        from apps.catalog.models import ProductPackaging, GrindType, RoastType
                        grind_whole, _ = GrindType.objects.get_or_create(
                            slug="whole", defaults={"name": "В зёрнах", "order": 0}
                        )
                        roast_slug = {"light": "light", "medium": "medium", "dark": "dark", "espresso": "espresso"}.get(
                            getattr(product, "roast_level", "") or "", "medium"
                        )
                        roast_obj = RoastType.objects.filter(slug=roast_slug).first() \
                            or RoastType.objects.get_or_create(slug="medium", defaults={"name": "Средняя", "order": 2})[0]
                        for w, p in variants_to_create.items():
                            pkg, _ = ProductPackaging.objects.update_or_create(
                                product=product, weight=w,
                                defaults={"price": p, "order": w},
                            )
                            ProductVariant.objects.update_or_create(
                                packaging=pkg, grind_type=grind_whole, roast_type=roast_obj,
                                defaults={"product": product, "sku": f"{slug}-{w}"}
                            )

                        if created: total_created += 1
                        else: total_updated += 1
                        total_found += 1

                        status = "CREATED" if created else "UPDATED"
                        v_counts = f"{list(variants_to_create.keys())}"
                        self.stdout.write(self.style.SUCCESS(f"    ✓ {status}: {name} | Variants: {v_counts}"))

                        total_handled += 1
                        time.sleep(0.05)
                    except Exception as ex:
                        self.stdout.write(self.style.ERROR(f"    FAILED: {slug} | {ex}"))
                        self.stdout.write(traceback.format_exc())
                page += 1
                if page > 20: break

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Parser MASTER CRASH: {e}"))
            self.stdout.write(traceback.format_exc())
        finally:
            if client:
                client.close()

        self.stdout.write(self.style.SUCCESS(f"\nDone. Processed {total_handled} products."))

    def _extract_nuxt(self, html):
        m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try: return json.loads(m.group(1))
            except: pass
        return None
