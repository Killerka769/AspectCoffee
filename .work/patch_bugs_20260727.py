#!/usr/bin/env python3
"""Apply mobile/catalog/checkout bugfixes on the Aspect Coffee VPS tree."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("/opt/aspectcoffee")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"FAIL {label}: pattern not found in {path}")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"FAIL {label}: expected 1 match, found {count} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"OK {label}")


def patch_product_card() -> None:
    path = ROOT / "apps/catalog/templates/catalog/_product_card.html"
    old = (
        '            <div class="tc-tooltip tc-card-process" '
        '@mouseenter="tooltipOpen = true" @mouseleave="tooltipOpen = false">\n'
        '                <div class="tc-tooltip__btn">\n'
        '                    {{ product.processing_method|default:"мытый" }}\n'
        "                </div>\n"
        '                <div class="tc-tooltip__content" x-show="tooltipOpen" '
        "x-transition x-cloak>\n"
        "                    <p>Обработка: {{ product.processing_method|default:"
        '"мытый" }}. Этот способ влияет на вкус — он определяет характер и чистоту '
        "профиля чашки.</p>\n"
        "                </div>\n"
        "            </div>"
    )
    new = (
        '            <div class="tc-tooltip tc-card-process" data-no-card-nav\n'
        '                 role="button" tabindex="0"\n'
        '                 aria-label="Подсказка: способ обработки"\n'
        '                 @click.stop="tooltipOpen = !tooltipOpen"\n'
        '                 @keydown.enter.prevent.stop="tooltipOpen = !tooltipOpen"\n'
        '                 @keydown.space.prevent.stop="tooltipOpen = !tooltipOpen"\n'
        '                 @mouseenter="tooltipOpen = true"\n'
        '                 @mouseleave="tooltipOpen = false">\n'
        '                <div class="tc-tooltip__btn">\n'
        '                    {{ product.processing_method|default:"мытый" }}\n'
        "                </div>\n"
        '                <div class="tc-tooltip__content" x-show="tooltipOpen" '
        "x-transition x-cloak @click.stop>\n"
        "                    <p>Обработка: {{ product.processing_method|default:"
        '"мытый" }}. Этот способ влияет на вкус — он определяет характер и чистоту '
        "профиля чашки.</p>\n"
        "                </div>\n"
        "            </div>"
    )
    replace_once(path, old, new, "product-card-tooltip")


def patch_navigate_card() -> None:
    path = ROOT / "static/asset/js/custom.js"
    old = (
        "        navigateCard(e) {\n"
        "            // Если открыт любой поповер карточки (выбор помола/обжарки или заметка) —\n"
        "            // не переходим на карточку: клик предназначен попап-меню, не навигации.\n"
        "            if (this.grindOpen || this.noteOpen) return;\n"
        "            // If user clicked any interactive element inside the card, do nothing.\n"
        "            let interactive = false;\n"
        "            if (typeof e.composedPath === 'function') {\n"
        "                interactive = e.composedPath().some(el => {\n"
        "                    if (el && el.matches) {\n"
        "                        return el.matches('a, button, select, input, textarea, label, [data-no-card-nav]');\n"
        "                    }\n"
        "                    return false;\n"
        "                });\n"
        "            } else {\n"
        "                interactive = e.target.closest('a, button, select, input, textarea, label, [data-no-card-nav]');\n"
        "            }\n"
    )
    new = (
        "        navigateCard(e) {\n"
        "            // Если открыт любой поповер карточки (выбор помола/обжарки, подсказка или заметка) —\n"
        "            // не переходим на карточку: клик предназначен попап-меню, не навигации.\n"
        "            if (this.grindOpen || this.noteOpen || this.tooltipOpen) return;\n"
        "            // If user clicked any interactive element inside the card, do nothing.\n"
        "            let interactive = false;\n"
        "            const interactiveSelector = 'a, button, select, input, textarea, label, [data-no-card-nav], .tc-tooltip';\n"
        "            if (typeof e.composedPath === 'function') {\n"
        "                interactive = e.composedPath().some(el => {\n"
        "                    if (el && el.matches) {\n"
        "                        return el.matches(interactiveSelector);\n"
        "                    }\n"
        "                    return false;\n"
        "                });\n"
        "            } else {\n"
        "                interactive = e.target.closest(interactiveSelector);\n"
        "            }\n"
    )
    replace_once(path, old, new, "navigateCard-tooltip")


def patch_catalog_filter_promo() -> None:
    path = ROOT / "apps/catalog/templates/catalog/catalog.html"
    text = path.read_text(encoding="utf-8")
    start = text.find("          {% if not user.is_authenticated %}\n          <div class=\"w-full bg-white rounded-3xl h-full p-6 flex flex-col justify-between mb-6\">")
    if start < 0:
        raise SystemExit("FAIL filter-promo: start not found")
    # End of guest/auth promo block before the count paragraph
    end_marker = "          {% endif %}\n\n          <div class=\"w-full mb-4\">\n            <p class=\"text-[var(--black-50)] mb-4 leading-8\">"
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("FAIL filter-promo: end marker not found")
    promo_block = text[start:end]
    without_promo = text[:start] + text[end:]
    # Insert before closing of tc-sidebar__inner (the blank line before </div>\n      </aside>)
    anchor = "\n\n        </div>\n      </aside>"
    if anchor not in without_promo:
        raise SystemExit("FAIL filter-promo: sidebar close anchor not found")
    patched = without_promo.replace(anchor, "\n\n" + promo_block + anchor, 1)
    path.write_text(patched, encoding="utf-8")
    print("OK filter-promo-moved-below")


def patch_basket_cart_overlap() -> None:
    path = ROOT / "apps/orders/templates/orders/basket.html"
    old = (
        '<div class="space-y-2 pl-2 xl:pl-4 max-w-[calc(100%-96px)] xl:max-w-[calc(100%-80px)] '
        'w-full max-xl:flex max-xl:flex-col max-xl:pr-10 max-xl:pt-1">\n'
        '<a class="text-[24px] text-black font-din-black uppercase leading-[1.2] tracking-[0.4px] m-0" '
        'href="{{ item.variant.product.get_absolute_url }}">{{ item.variant.product.name }}</a>'
    )
    new = (
        '<div class="tc-cart-item-info space-y-2 pl-2 xl:pl-4 max-w-[calc(100%-96px)] '
        'xl:max-w-[calc(100%-80px)] w-full max-xl:flex max-xl:flex-col max-xl:pt-1">\n'
        '<a class="tc-cart-item-title text-[24px] text-black font-din-black uppercase leading-[1.2] '
        'tracking-[0.4px] m-0" href="{{ item.variant.product.get_absolute_url }}">'
        "{{ item.variant.product.name }}</a>"
    )
    replace_once(path, old, new, "cart-title-classes")

    old_btn = (
        '<button class="tc-btn btn-secondary-sm px-1 xl:ml-6 max-xl:!absolute max-xl:top-0 '
        'max-xl:right-0 !min-w-[32px]" onclick="tcRemoveFromCart({{ item.variant.id }})" '
        'type="button"><svg class="ic-right"><use href="{% static \'asset/images/sprite.svg\' %}'
        '#icons--delete"></use></svg></button>'
    )
    new_btn = (
        '<button class="tc-cart-remove tc-btn btn-secondary-sm px-1 xl:ml-6 max-xl:!absolute '
        'max-xl:top-0 max-xl:right-0 !min-w-[32px]" onclick="tcRemoveFromCart({{ item.variant.id }})" '
        'type="button" aria-label="Удалить товар"><svg class="ic-right">'
        '<use href="{% static \'asset/images/sprite.svg\' %}#icons--delete"></use></svg></button>'
    )
    replace_once(path, old_btn, new_btn, "cart-remove-class")

    style_anchor = "@media(max-width:1099px){\n    #basket-left-col{display:flex;flex-direction:column;gap:12px}"
    style_inject = (
        "@media(max-width:1099px){\n"
        "    #basket-left-col li[data-variant-id] .tc-cart-item-info{"
        "padding-right:44px;box-sizing:border-box;}\n"
        "    #basket-left-col li[data-variant-id] .tc-cart-item-title{"
        "display:block;overflow-wrap:anywhere;word-break:break-word;}\n"
        "    #basket-left-col li[data-variant-id] .tc-cart-remove{"
        "z-index:2;}\n"
        "    #basket-left-col{display:flex;flex-direction:column;gap:12px}"
    )
    replace_once(path, style_anchor, style_inject, "cart-overlap-css")


def patch_basket_phone_and_checkout() -> None:
    path = ROOT / "apps/orders/templates/orders/basket.html"
    text = path.read_text(encoding="utf-8")

    # Mobile phone: show +code and use improved mask
    old_mobile_phone = (
        '<input :class="errors.phone && \'border-red-500\'" @change="checkValidation()" '
        '@input="checkValidation()" class="tc-input__field--input w-full" name="phone_m" '
        'oninput="tcPhoneMask(event)" placeholder="Телефон" type="tel" '
        'value="{{ user.phone|default:\'\' }}" x-bind:data-phone-length="phoneLength" '
        'x-bind:maxlength="phoneLength + 6"/>'
    )
    new_mobile_phone = (
        '<div class="tc-phone__field items-stretch">\n'
        '<div class="tc-select phone-select flex-none" style="min-width:72px">'
        '<div class="tc-select__field">'
        '<div class="tc-select__field--select cursor-default">'
        '<span class="select-text" x-text="phoneCode">+7</span>'
        "</div></div></div>\n"
        '<input :value="phoneCode" name="phone_code" type="hidden"/>\n'
        '<input :class="errors.phone && \'border-red-500\'" @change="checkValidation()" '
        '@input="checkValidation()" class="tc-input__field--input w-full" name="phone_m" '
        'oninput="tcPhoneMask(event)" placeholder="(900) 000-00-00" type="tel" '
        'value="{{ user.phone|default:\'\' }}" x-bind:data-phone-length="phoneLength" '
        'x-bind:maxlength="phoneLength + 6"/>\n'
        "</div>"
    )
    if old_mobile_phone not in text:
        raise SystemExit("FAIL mobile-phone: pattern not found")
    text = text.replace(old_mobile_phone, new_mobile_phone, 1)

    # Improve inline tcPhoneMask to strip leading 8/7 for RU numbers
    old_mask = (
        "function tcPhoneMask(e) {\n"
        "    var el = e.target;\n"
        "    var len = parseInt(el.getAttribute('data-phone-length')) || 10;\n"
        "    var raw = el.value.replace(/\\D/g, '').slice(0, len);\n"
        "    if (!raw) { el.value = ''; return; }\n"
        "    var f = '';\n"
        "    if (raw.length <= 3) {\n"
        "        f = '(' + raw;\n"
        "    } else if (raw.length <= 6) {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3);\n"
        "    } else if (raw.length <= 8) {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3,6) + '-' + raw.slice(6);\n"
        "    } else {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3,6) + '-' + raw.slice(6,8) + '-' + raw.slice(8);\n"
        "    }\n"
        "    el.value = f;\n"
        "}"
    )
    new_mask = (
        "function tcPhoneMask(e) {\n"
        "    var el = e.target;\n"
        "    var len = parseInt(el.getAttribute('data-phone-length')) || 10;\n"
        "    var raw = el.value.replace(/\\D/g, '');\n"
        "    // 8XXXXXXXXXX / 7XXXXXXXXXX / +7XXXXXXXXXX → local 10 digits for RU\n"
        "    if (raw.length >= 11 && (raw[0] === '8' || raw[0] === '7')) {\n"
        "        raw = raw.slice(1);\n"
        "    }\n"
        "    raw = raw.slice(0, len);\n"
        "    if (!raw) { el.value = ''; return; }\n"
        "    var f = '';\n"
        "    if (raw.length <= 3) {\n"
        "        f = '(' + raw;\n"
        "    } else if (raw.length <= 6) {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3);\n"
        "    } else if (raw.length <= 8) {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3,6) + '-' + raw.slice(6);\n"
        "    } else {\n"
        "        f = '(' + raw.slice(0,3) + ') ' + raw.slice(3,6) + '-' + raw.slice(6,8) + '-' + raw.slice(8);\n"
        "    }\n"
        "    el.value = f;\n"
        "}"
    )
    if old_mask not in text:
        raise SystemExit("FAIL phone-mask: pattern not found")
    text = text.replace(old_mask, new_mask, 1)

    # Checkout submit: disable hidden recipient fields + always restore button
    old_submit = (
        "                const btn = document.querySelector('[data-checkout-submit]');\n"
        "                if (btn) { btn.disabled = true; btn.textContent = 'Оформляем...'; }\n"
        "                const fd = new FormData(document.getElementById('basket-form'));\n"
        "                fd.set('action', 'checkout');\n"
        "                fd.set('selected_address_id', this.selectedAddressId || '');\n"
        "                fd.set('delivery_type', this.deliveryType);\n"
        "                fd.set('payment_method', this.paymentMethod);\n"
        "                if (this.deliveryType === 'cdek_pvz' || this.deliveryType === 'cdek_door') {\n"
        "                    fd.set('cdek_city_code', this.cdekSelectedCity ? this.cdekSelectedCity.code : '');\n"
        "                    fd.set('cdek_city_name', this.cdekCityQuery || (this.cdekSelectedCity ? this.cdekSelectedCity.city : ''));\n"
        "                    fd.set('cdek_street', this.getValue(['street', 'street_m']));\n"
        "                    fd.set('cdek_house', this.getValue(['house', 'house_m']));\n"
        "                    fd.set('cdek_apartment', this.getValue(['apartment', 'apt_m']));\n"
        "                    fd.set('cdek_postal_code', this.getValue(['postal_code', 'postal_code_m']));\n"
        "                }\n"
        "                fetch(window.location.pathname, { method: 'POST', body: fd, headers: {'X-Requested-With': 'XMLHttpRequest'} })\n"
        "                    .then(r => r.text().then(text => {\n"
        "                        let data;\n"
        "                        try { data = JSON.parse(text); } catch(err) { data = null; }\n"
        "                        if (data && data.redirect_url) {\n"
        "                            window.location.href = data.redirect_url;\n"
        "                        } else if (data && data.error) {\n"
        "                            this.showToast(data.error, 'error');\n"
        "                            if (btn) { btn.disabled = false; btn.textContent = 'Оформить заказ'; }\n"
        "                        } else {\n"
        "                            window.location.reload();\n"
        "                        }\n"
        "                    }))\n"
        "                    .catch(() => {\n"
        "                        this.showToast('Ошибка сети', 'error');\n"
        "                        if (btn) { btn.disabled = false; btn.textContent = 'Оформить заказ'; }\n"
        "                    });\n"
    )
    new_submit = (
        "                const btn = document.querySelector('[data-checkout-submit]');\n"
        "                const resetBtn = () => { if (btn) { btn.disabled = false; btn.textContent = 'Оформить заказ'; } };\n"
        "                if (btn) { btn.disabled = true; btn.textContent = 'Оформляем...'; }\n"
        "                const form = document.getElementById('basket-form');\n"
        "                // Hidden desktop/mobile duplicates must not override visible values.\n"
        "                form.querySelectorAll('.recipient-desktop, .recipient-mobile, .delivery-desktop, .delivery-mobile').forEach(block => {\n"
        "                    const hidden = window.getComputedStyle(block).display === 'none';\n"
        "                    block.querySelectorAll('input, textarea, select').forEach(el => { el.disabled = hidden; });\n"
        "                });\n"
        "                const fd = new FormData(form);\n"
        "                form.querySelectorAll('.recipient-desktop input, .recipient-mobile input, .delivery-desktop input, .delivery-mobile input, .recipient-desktop textarea, .recipient-mobile textarea, .delivery-desktop textarea, .delivery-mobile textarea, .recipient-desktop select, .recipient-mobile select, .delivery-desktop select, .delivery-mobile select').forEach(el => { el.disabled = false; });\n"
        "                fd.set('action', 'checkout');\n"
        "                fd.set('selected_address_id', this.selectedAddressId || '');\n"
        "                fd.set('delivery_type', this.deliveryType);\n"
        "                fd.set('payment_method', this.paymentMethod);\n"
        "                fd.set('full_name', this.getValue(['full_name', 'full_name_m']));\n"
        "                fd.set('phone', this.getValue(['phone', 'phone_m']));\n"
        "                fd.set('phone_code', this.phoneCode || '+7');\n"
        "                fd.set('email', this.getValue(['email', 'email_m']));\n"
        "                if (this.deliveryType === 'cdek_pvz' || this.deliveryType === 'cdek_door') {\n"
        "                    fd.set('cdek_city_code', this.cdekSelectedCity ? this.cdekSelectedCity.code : '');\n"
        "                    fd.set('cdek_city_name', this.cdekCityQuery || (this.cdekSelectedCity ? this.cdekSelectedCity.city : ''));\n"
        "                    fd.set('cdek_street', this.getValue(['street', 'street_m']));\n"
        "                    fd.set('cdek_house', this.getValue(['house', 'house_m']));\n"
        "                    fd.set('cdek_apartment', this.getValue(['apartment', 'apt_m']));\n"
        "                    fd.set('cdek_postal_code', this.getValue(['postal_code', 'postal_code_m']));\n"
        "                }\n"
        "                fetch(window.location.pathname, { method: 'POST', body: fd, headers: {'X-Requested-With': 'XMLHttpRequest'} })\n"
        "                    .then(r => r.text().then(text => {\n"
        "                        let data;\n"
        "                        try { data = JSON.parse(text); } catch(err) { data = null; }\n"
        "                        if (data && data.redirect_url) {\n"
        "                            window.location.href = data.redirect_url;\n"
        "                            return;\n"
        "                        }\n"
        "                        if (data && data.error) {\n"
        "                            this.showToast(data.error, 'error');\n"
        "                            resetBtn();\n"
        "                            return;\n"
        "                        }\n"
        "                        if (!r.ok) {\n"
        "                            this.showToast('Не удалось оформить заказ. Попробуйте ещё раз.', 'error');\n"
        "                            resetBtn();\n"
        "                            return;\n"
        "                        }\n"
        "                        window.location.reload();\n"
        "                    }))\n"
        "                    .catch(() => {\n"
        "                        this.showToast('Ошибка сети', 'error');\n"
        "                        resetBtn();\n"
        "                    });\n"
    )
    if old_submit not in text:
        raise SystemExit("FAIL checkout-submit: pattern not found")
    text = text.replace(old_submit, new_submit, 1)

    # Recurring UI: temporary 10-minute test interval
    old_repeat = (
        "            repeatOn: false,\n"
        "            repeatWeeks: 1,\n"
    )
    new_repeat = (
        "            repeatOn: false,\n"
        "            repeatWeeks: 1,\n"
        "            // TEMP test mode: auto-repeat every 10 minutes (not weeks).\n"
        "            repeatTestMinutes: 10,\n"
    )
    if old_repeat not in text:
        raise SystemExit("FAIL repeat-state: pattern not found")
    text = text.replace(old_repeat, new_repeat, 1)

    old_repeat_ui = (
        '<input type="hidden" name="repeat_weeks" :value="repeatWeeks"/>\n'
        '<div x-show="repeatOn && paymentMethod === \'card\'"\n'
    )
    # Need more context - get exact block
    path.write_text(text, encoding="utf-8")
    print("OK basket-phone-checkout-partial")


def patch_basket_repeat_ui() -> None:
    path = ROOT / "apps/orders/templates/orders/basket.html"
    text = path.read_text(encoding="utf-8")
    old = (
        '<input type="hidden" name="repeat_order" :value="repeatOn && paymentMethod === \'card\' ? \'on\' : \'"/>\n'
        '<input type="hidden" name="repeat_weeks" :value="repeatWeeks"/>\n'
        '<div x-show="repeatOn && paymentMethod === \'card\'"'
    )
    # Find the exact lines around repeat UI
    idx = text.find('name="repeat_weeks"')
    if idx < 0:
        raise SystemExit("FAIL repeat-ui: repeat_weeks not found")
    snippet = text[idx - 120 : idx + 450]
    print("REPEAT SNIPPET:\n", snippet)


def patch_views_phone_name() -> None:
    path = ROOT / "apps/orders/views.py"
    old = (
        "            # Extract and split names, handling both mobile and desktop form fields\n"
        '            full_name = (request.POST.get("full_name") or request.POST.get("full_name_m") or "").strip()\n'
        '            first_name = request.POST.get("first_name", "")\n'
        '            last_name = request.POST.get("last_name", "")\n'
        "            if full_name and not first_name:\n"
        "                parts = full_name.split(None, 1)\n"
        "                first_name = parts[0]\n"
        "                if len(parts) > 1:\n"
        "                    last_name = parts[1]\n"
        "\n"
        '            phone = (request.POST.get("phone", "") or request.POST.get("phone_m", "")).strip()\n'
        '            phone_code = request.POST.get("phone_code", "+7")\n'
        '            raw_phone_digits = "".join(ch for ch in phone if ch.isdigit())\n'
        "            if len(raw_phone_digits) < 7:\n"
        '                raise ValueError("Укажите корректный телефон")\n'
        '            code_digits = "".join(ch for ch in phone_code if ch.isdigit())\n'
        "            if raw_phone_digits.startswith(code_digits):\n"
        '                phone = f"{phone_code}{raw_phone_digits[len(code_digits):]}"\n'
        "            else:\n"
        '                phone = f"{phone_code}{raw_phone_digits}"\n'
    )
    new = (
        "            # Prefer non-empty values across desktop/mobile duplicates.\n"
        "            def _post_first(*names):\n"
        "                values = [(request.POST.get(name) or \"\").strip() for name in names]\n"
        "                nonempty = [v for v in values if v]\n"
        "                return max(nonempty, key=len) if nonempty else \"\"\n"
        "\n"
        '            full_name = _post_first("full_name", "full_name_m")\n'
        '            first_name = (request.POST.get("first_name") or "").strip()\n'
        '            last_name = (request.POST.get("last_name") or "").strip()\n'
        "            if full_name and not first_name:\n"
        "                parts = full_name.split(None, 1)\n"
        "                first_name = parts[0]\n"
        "                if len(parts) > 1:\n"
        "                    last_name = parts[1]\n"
        "\n"
        '            phone = _post_first("phone", "phone_m")\n'
        '            phone_code = (request.POST.get("phone_code") or "+7").strip() or "+7"\n'
        '            raw_phone_digits = "".join(ch for ch in phone if ch.isdigit())\n'
        "            # Normalize classic RU formats: 8XXXXXXXXXX / 7XXXXXXXXXX\n"
        "            if len(raw_phone_digits) >= 11 and raw_phone_digits[0] in {\"7\", \"8\"}:\n"
        "                raw_phone_digits = raw_phone_digits[1:]\n"
        "                phone_code = \"+7\"\n"
        "            if len(raw_phone_digits) < 7:\n"
        '                raise ValueError("Укажите корректный телефон")\n'
        '            code_digits = "".join(ch for ch in phone_code if ch.isdigit())\n'
        "            if code_digits and raw_phone_digits.startswith(code_digits):\n"
        '                phone = f"{phone_code}{raw_phone_digits[len(code_digits):]}"\n'
        "            else:\n"
        '                phone = f"{phone_code}{raw_phone_digits}"\n'
    )
    replace_once(path, old, new, "views-name-phone")


def patch_recurring_interval() -> None:
    """Temporary 10-minute auto-repeat for testing auto-debit."""
    for rel, old, new, label in [
        (
            "apps/payments/services.py",
            "                    recurring_plan.next_charge_at = timezone.now() + timedelta(\n"
            "                        weeks=recurring_plan.interval_weeks\n"
            "                    )\n",
            "                    # TEMP: 10 minutes for auto-repeat testing (was weeks=interval_weeks).\n"
            "                    recurring_plan.next_charge_at = timezone.now() + timedelta(minutes=10)\n",
            "payments-services-interval",
        ),
        (
            "apps/payments/tasks.py",
            "            plan.next_charge_at = max(scheduled_for, now) + timedelta(weeks=plan.interval_weeks)\n",
            "            # TEMP: 10 minutes for auto-repeat testing (was weeks=interval_weeks).\n"
            "            plan.next_charge_at = max(scheduled_for, now) + timedelta(minutes=10)\n",
            "payments-tasks-interval",
        ),
        (
            "apps/orders/admin.py",
            "                plan.next_charge_at = now + timedelta(weeks=plan.interval_weeks)\n",
            "                # TEMP: 10 minutes for auto-repeat testing (was weeks=interval_weeks).\n"
            "                plan.next_charge_at = now + timedelta(minutes=10)\n",
            "orders-admin-interval",
        ),
    ]:
        replace_once(ROOT / rel, old, new, label)

    # Also set next_charge when creating RecurringOrder in views
    views = ROOT / "apps/orders/views.py"
    text = views.read_text(encoding="utf-8")
    needle = "recurring_plan = RecurringOrder.objects.create("
    idx = text.find(needle)
    if idx < 0:
        raise SystemExit("FAIL views-recurring-create: not found")
    chunk = text[idx : idx + 500]
    print("RECURRING CREATE CHUNK:\n", chunk)


def patch_basket_repeat_display() -> None:
    path = ROOT / "apps/orders/templates/orders/basket.html"
    text = path.read_text(encoding="utf-8")
    old = (
        '<div class="flex items-center gap-2 text-[14px] mb-3"><span>каждые</span>'
        '<input class="w-14 text-center bg-[#f5f5f5] border-0 rounded-lg px-2 py-2 font-bold '
        'focus:outline-none" max="12" min="1" type="number" x-model.number="repeatWeeks"/>'
        "<span>нед.</span></div>\n"
        '<p class="text-[12px] text-black/55 leading-[1.45]" '
        "x-text=\"'После первой успешной оплаты карта будет безопасно сохранена в ЮKassa. "
        "Следующее списание — через ' + (repeatWeeks * 7) + ' дней.'\"></p>"
    )
    new = (
        '<div class="flex items-center gap-2 text-[14px] mb-3">'
        "<span>каждые</span>"
        '<span class="font-bold px-2 py-2 rounded-lg bg-[#f5f5f5]">10 мин.</span>'
        '<span class="text-[12px] text-amber-700">(тест автосписания)</span></div>\n'
        '<input type="hidden" name="repeat_weeks" :value="repeatWeeks"/>\n'
        '<p class="text-[12px] text-black/55 leading-[1.45]">'
        "После первой успешной оплаты карта будет безопасно сохранена в ЮKassa. "
        "Следующее тестовое списание — через 10 минут.</p>"
    )
    # There may already be a hidden repeat_weeks above — remove duplicate carefully
    if 'x-text="\'После первой успешной оплаты' not in text and "Следующее списание — через" not in text:
        # try alternate apostrophe
        pass
    if old not in text:
        # Show nearby content for debugging
        idx = text.find("каждые")
        print(repr(text[idx : idx + 400]))
        raise SystemExit("FAIL repeat-display: pattern not found")
    # Remove the earlier hidden repeat_weeks if present to avoid duplicates
    text = text.replace(
        '<input type="hidden" name="repeat_weeks" :value="repeatWeeks"/>\n',
        "",
        1,
    )
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("OK repeat-display")


def patch_phone_utils() -> None:
    path = ROOT / "static/asset/js/phone_utils.js"
    old = (
        "    stripInput: function(alpineData, inputName) {\n"
        "        inputName = inputName || 'phone';\n"
        "        var phoneInput = document.querySelector('input[name=\"' + inputName + '\"]');\n"
        "        if (!phoneInput || !phoneInput.value) return;\n"
        "        var detected = this.detectCode(phoneInput.value);\n"
        "        if (detected) {\n"
        "            alpineData.phoneCode = detected.code;\n"
        "            alpineData.phoneLength = detected.length;\n"
        "            phoneInput.value = detected.local;\n"
        "        }\n"
        "    },\n"
    )
    new = (
        "    stripInput: function(alpineData, inputName) {\n"
        "        inputName = inputName || 'phone';\n"
        "        var names = inputName === 'phone' ? ['phone', 'phone_m'] : [inputName];\n"
        "        for (var n = 0; n < names.length; n++) {\n"
        "            var phoneInput = document.querySelector('input[name=\"' + names[n] + '\"]');\n"
        "            if (!phoneInput || !phoneInput.value) continue;\n"
        "            var detected = this.detectCode(phoneInput.value);\n"
        "            if (detected) {\n"
        "                alpineData.phoneCode = detected.code;\n"
        "                alpineData.phoneLength = detected.length;\n"
        "                phoneInput.value = detected.local;\n"
        "                this.mask({target: phoneInput}, detected.length);\n"
        "            }\n"
        "        }\n"
        "    },\n"
    )
    replace_once(path, old, new, "phone-utils-strip")

    old_mask = (
        "    mask: function(e, phoneLength) {\n"
        "        var el = e.target || e;\n"
        "        var v = el.value.replace(/[^0-9]/g, '').substring(0, phoneLength);\n"
    )
    new_mask = (
        "    mask: function(e, phoneLength) {\n"
        "        var el = e.target || e;\n"
        "        var v = el.value.replace(/[^0-9]/g, '');\n"
        "        if (v.length >= 11 && (v[0] === '8' || v[0] === '7')) {\n"
        "            v = v.substring(1);\n"
        "        }\n"
        "        v = v.substring(0, phoneLength);\n"
    )
    replace_once(path, old_mask, new_mask, "phone-utils-mask")


def patch_views_recurring_create() -> None:
    path = ROOT / "apps/orders/views.py"
    text = path.read_text(encoding="utf-8")
    old = None
    # Find create call
    import re

    m = re.search(
        r"recurring_plan = RecurringOrder\.objects\.create\(\n(?:.*\n){1,12}?\s*\)",
        text,
    )
    if not m:
        raise SystemExit("FAIL views-recurring-create-regex")
    block = m.group(0)
    if "next_charge_at" in block:
        print("OK views-recurring-create already has next_charge_at")
        return
    # Inject next_charge_at
    if "interval_weeks=repeat_weeks," not in block:
        raise SystemExit("FAIL views-recurring-create: interval_weeks missing")
    new_block = block.replace(
        "interval_weeks=repeat_weeks,",
        "interval_weeks=repeat_weeks,\n"
        "                    # TEMP test: first charge in 10 minutes after payment activation.\n"
        "                    next_charge_at=timezone.now() + timedelta(minutes=10),",
    )
    # Ensure imports
    if "from datetime import timedelta" not in text and "timedelta" not in text[:2000]:
        # views likely already imports timezone
        pass
    if "timedelta" not in text:
        text = text.replace(
            "from django.utils import timezone",
            "from datetime import timedelta\nfrom django.utils import timezone",
            1,
        )
    elif "from datetime import timedelta" not in text and "import timedelta" not in text:
        # timedelta used elsewhere via datetime import?
        if "from datetime import" in text:
            text = text.replace("from datetime import ", "from datetime import timedelta, ", 1)
        else:
            text = "from datetime import timedelta\n" + text
    text = text.replace(block, new_block, 1)
    path.write_text(text, encoding="utf-8")
    print("OK views-recurring-create")


def main() -> None:
    patch_product_card()
    patch_navigate_card()
    patch_catalog_filter_promo()
    patch_basket_cart_overlap()
    patch_basket_phone_and_checkout()
    patch_basket_repeat_display()
    patch_views_phone_name()
    patch_recurring_interval()
    patch_views_recurring_create()
    patch_phone_utils()
    print("ALL PATCHES APPLIED")


if __name__ == "__main__":
    main()
