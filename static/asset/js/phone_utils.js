/* Aspect Coffee phone system.
 * Country metadata comes from apps.users.phone_countries and is shared by
 * registration, OAuth completion, profile and checkout.
 */
(function (window, document) {
    "use strict";

    var codes = Array.isArray(window.TC_PHONE_COUNTRIES)
        ? window.TC_PHONE_COUNTRIES
        : [];

    function digits(value) {
        return String(value || "").replace(/\D/g, "");
    }

    function byCode(code) {
        return codes.find(function (item) {
            return item.code === code;
        }) || codes[0] || {
            code: "+7",
            country: "Россия / Казахстан",
            length: 10,
            fmt: "(000) 000-00-00",
            placeholder: "(900) 000-00-00"
        };
    }

    function formatNational(value, country) {
        var raw = digits(value).slice(0, country.length);
        if (!raw) return "";

        var result = "";
        var position = 0;
        for (var i = 0; i < country.fmt.length && position < raw.length; i++) {
            var token = country.fmt.charAt(i);
            if (token === "0") {
                result += raw.charAt(position++);
            } else if (position > 0 && position < raw.length) {
                result += token;
            }
        }
        return result;
    }

    function nationalDigits(value, country) {
        var raw = digits(value);
        var prefix = digits(country.code);

        if (String(value || "").trim().charAt(0) === "+" && raw.indexOf(prefix) === 0) {
            raw = raw.slice(prefix.length);
        } else if (raw.indexOf(prefix) === 0 && raw.length > country.length) {
            raw = raw.slice(prefix.length);
        } else if (country.code === "+7" && raw.length === 11 && raw.charAt(0) === "8") {
            raw = raw.slice(1);
        }
        return raw.slice(0, country.length);
    }

    function countryForInput(input, fallback) {
        var group = input && input.closest
            ? input.closest("[data-aspect-phone-group]")
            : null;
        var hidden = group
            ? group.querySelector("[data-aspect-phone-code]")
            : null;
        var inputCode = input && input.getAttribute
            ? input.getAttribute("data-phone-code")
            : "";
        var code = hidden && hidden.value ? hidden.value : (inputCode || fallback);
        return byCode(code);
    }

    function applyCountry(group, code, options) {
        if (!group) return;
        var country = byCode(code);
        var hidden = group.querySelector("[data-aspect-phone-code]");
        var label = group.querySelector("[data-aspect-phone-code-label]");
        var inputs = group.querySelectorAll("[data-aspect-phone-input]");

        if (hidden) hidden.value = country.code;
        if (label) label.textContent = country.code;
        group.setAttribute("data-phone-code", country.code);
        group.setAttribute("data-phone-length", String(country.length));

        inputs.forEach(function (input) {
            var raw = nationalDigits(input.value, country);
            input.setAttribute("data-phone-length", String(country.length));
            input.setAttribute("data-phone-code", country.code);
            input.setAttribute("maxlength", String(country.fmt.length));
            input.setAttribute("placeholder", country.placeholder || country.fmt);
            input.value = formatNational(raw, country);
            validateInput(input, country, false);
        });

        group.querySelectorAll("[data-aspect-phone-option]").forEach(function (option) {
            option.classList.toggle(
                "is-active",
                option.getAttribute("data-code") === country.code
            );
        });

        var menu = group.querySelector("[data-aspect-phone-menu]");
        var trigger = group.querySelector("[data-aspect-phone-trigger]");
        if (menu) menu.hidden = true;
        if (trigger) trigger.setAttribute("aria-expanded", "false");

        group.dispatchEvent(new CustomEvent("tcphone:change", {
            bubbles: true,
            detail: {
                code: country.code,
                length: country.length,
                format: country.fmt
            }
        }));

        if (options && options.focus && inputs[0]) inputs[0].focus();
    }

    function validateInput(input, country, showMessage) {
        var count = nationalDigits(input.value, country).length;
        var valid = count === 0 || count === country.length;
        input.setCustomValidity(
            valid || !showMessage
                ? ""
                : "Введите " + country.length + " цифр после кода " + country.code
        );
        input.setAttribute("data-phone-valid", valid ? "true" : "false");
        return valid;
    }

    function renderMenu(group) {
        var menu = group.querySelector("[data-aspect-phone-menu]");
        if (!menu || menu.childElementCount) return;

        codes.forEach(function (country) {
            var option = document.createElement("button");
            option.type = "button";
            option.className = "aspect-phone-country-option";
            option.setAttribute("data-aspect-phone-option", "");
            option.setAttribute("data-code", country.code);
            option.innerHTML =
                '<span class="aspect-phone-country-option__code"></span>' +
                '<span class="aspect-phone-country-option__name"></span>';
            option.querySelector(".aspect-phone-country-option__code").textContent = country.code;
            option.querySelector(".aspect-phone-country-option__name").textContent = country.country;
            option.addEventListener("click", function () {
                applyCountry(group, country.code, {focus: true});
            });
            menu.appendChild(option);
        });
    }

    function mount(group) {
        if (!group || group.getAttribute("data-aspect-phone-mounted") === "true") return;
        group.setAttribute("data-aspect-phone-mounted", "true");
        renderMenu(group);

        var hidden = group.querySelector("[data-aspect-phone-code]");
        var firstInput = group.querySelector("[data-aspect-phone-input]");
        var initialCode = hidden && hidden.value ? hidden.value : group.getAttribute("data-phone-code");
        var detected = firstInput && firstInput.value
            ? TCPhone.detectCode(firstInput.value)
            : null;
        var code = detected ? detected.code : (initialCode || "+7");

        if (detected && firstInput) firstInput.value = detected.local;
        applyCountry(group, code);

        group.querySelectorAll("[data-aspect-phone-input]").forEach(function (input) {
            input.addEventListener("input", function () {
                var country = countryForInput(input, code);
                input.value = formatNational(nationalDigits(input.value, country), country);
                validateInput(input, country, true);
            });
            input.addEventListener("blur", function () {
                validateInput(input, countryForInput(input, code), true);
            });
        });

        var trigger = group.querySelector("[data-aspect-phone-trigger]");
        var menu = group.querySelector("[data-aspect-phone-menu]");
        if (trigger && menu) {
            trigger.addEventListener("click", function () {
                var willOpen = menu.hidden;
                document.querySelectorAll("[data-aspect-phone-menu]").forEach(function (other) {
                    other.hidden = true;
                });
                document.querySelectorAll("[data-aspect-phone-trigger]").forEach(function (other) {
                    other.setAttribute("aria-expanded", "false");
                });
                menu.hidden = !willOpen;
                trigger.setAttribute("aria-expanded", willOpen ? "true" : "false");
            });
        }
    }

    var TCPhone = {
        codes: codes,
        get: byCode,
        getCountry: function (code) {
            return byCode(code).country;
        },
        format: function (value, code) {
            var country = byCode(code);
            return formatNational(nationalDigits(value, country), country);
        },
        isComplete: function (value, code) {
            var country = byCode(code);
            return nationalDigits(value, country).length === country.length;
        },
        nationalDigits: function (value, code) {
            return nationalDigits(value, byCode(code));
        },
        detectCode: function (phone) {
            if (!phone) return null;
            var raw = digits(phone);
            var sorted = codes.slice().sort(function (left, right) {
                return digits(right.code).length - digits(left.code).length;
            });
            for (var i = 0; i < sorted.length; i++) {
                var country = sorted[i];
                var prefix = digits(country.code);
                if (String(phone).trim().charAt(0) === "+" && raw.indexOf(prefix) === 0) {
                    return {
                        code: country.code,
                        local: raw.slice(prefix.length),
                        length: country.length
                    };
                }
            }
            if (raw.length === 11 && raw.charAt(0) === "8") {
                return {code: "+7", local: raw.slice(1), length: 10};
            }
            return null;
        },
        mask: function (event, codeOrLength) {
            var input = event.target || event;
            var country = countryForInput(
                input,
                typeof codeOrLength === "string" ? codeOrLength : "+7"
            );
            if (typeof codeOrLength === "number" && !input.closest("[data-aspect-phone-group]")) {
                country = Object.assign({}, country, {length: codeOrLength});
            }
            input.value = formatNational(nationalDigits(input.value, country), country);
            validateInput(input, country, true);
        },
        selectCode: function (code, alpineData, root) {
            var country = byCode(code);
            if (alpineData) {
                alpineData.phoneCode = country.code;
                alpineData.phoneLength = country.length;
                alpineData.phoneFmt = country.placeholder || country.fmt;
                alpineData.phoneCodeOpen = false;
                alpineData.recipientPhoneCodeOpen = false;
            }
            if (root) {
                root.querySelectorAll("[data-aspect-phone-group]").forEach(function (group) {
                    applyCountry(group, country.code);
                });
            }
        },
        stripInput: function (alpineData, inputName) {
            var names = inputName === "phone"
                ? ["phone", "phone_m"]
                : [inputName || "phone"];
            for (var i = 0; i < names.length; i++) {
                var input = document.querySelector('input[name="' + names[i] + '"]');
                if (!input || !input.value) continue;
                var detected = this.detectCode(input.value);
                if (!detected) continue;
                if (alpineData) {
                    alpineData.phoneCode = detected.code;
                    alpineData.phoneLength = detected.length;
                }
                input.value = detected.local;
                var group = input.closest("[data-aspect-phone-group]");
                if (group) applyCountry(group, detected.code);
                else this.mask(input, detected.code);
            }
        },
        mount: mount,
        mountAll: function (root) {
            (root || document).querySelectorAll("[data-aspect-phone-group]").forEach(mount);
        },
        applyCountry: applyCountry
    };

    window.TCPhone = TCPhone;
    window.tcPhoneMask = function (event) {
        TCPhone.mask(event);
    };
    window.tcProfilePhoneMask = window.tcPhoneMask;

    function closeMenus(event) {
        document.querySelectorAll("[data-aspect-phone-group]").forEach(function (group) {
            if (group.contains(event.target)) return;
            var menu = group.querySelector("[data-aspect-phone-menu]");
            var trigger = group.querySelector("[data-aspect-phone-trigger]");
            if (menu) menu.hidden = true;
            if (trigger) trigger.setAttribute("aria-expanded", "false");
        });
    }

    document.addEventListener("click", closeMenus);
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            TCPhone.mountAll(document);
        });
    } else {
        TCPhone.mountAll(document);
    }
})(window, document);
