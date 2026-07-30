import re

with open("/opt/aspectcoffee/apps/orders/templates/orders/basket.html") as f:
    content = f.read()

# Add stripPhone method before selectAddress
strip_phone_method = """
            stripPhone() {
                const phoneCodes = this.phoneCodes;
                const phoneInput = document.querySelector('input[name=phone]');
                if (!phoneInput) return;
                let val = phoneInput.value.trim();
                if (!val) return;
                // detect code from stored value
                for (const c of phoneCodes) {
                    const codeDigits = c.code.replace('+', '');
                    if (val.startsWith(c.code) || val.startsWith('+' + codeDigits)) {
                        this.phoneCode = c.code;
                        this.phoneLength = c.length;
                        phoneInput.value = val.substring(c.code.length);
                        return;
                    }
                    if (val.startsWith(codeDigits)) {
                        this.phoneCode = '+' + codeDigits;
                        this.phoneLength = c.length;
                        phoneInput.value = val.substring(codeDigits.length);
                        return;
                    }
                }
                // also check for 8 prefix (old Russian format)
                if (val.startsWith('8') && val.length >= 11) {
                    this.phoneCode = '+7';
                    this.phoneLength = 10;
                    phoneInput.value = val.substring(1);
                }
            },"""

content = content.replace(
    "            selectAddress(id, city, street, apartment) {",
    strip_phone_method + "\n            selectAddress(id, city, street, apartment) {"
)

# Add stripPhone() call to x-init
old_init = 'x-init="initCitySync(); checkValidation(); setInterval(() => checkValidation(), 500);'
new_init = 'x-init="initCitySync(); stripPhone(); checkValidation(); setInterval(() => checkValidation(), 500);'
content = content.replace(old_init, new_init)

with open("/opt/aspectcoffee/apps/orders/templates/orders/basket.html", "w") as f:
    f.write(content)

# Verify
with open("/opt/aspectcoffee/apps/orders/templates/orders/basket.html") as f:
    c = f.read()
assert 'stripPhone()' in c, "stripPhone method not found"
assert 'stripPhone(); checkValidation()' in c, "stripPhone not in x-init"
print("OK: stripPhone added and called in x-init")
