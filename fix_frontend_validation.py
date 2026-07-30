import os

path = '/app/apps/orders/templates/orders/basket.html'
with open(path, 'r') as f:
    content = f.read()

old = """                if (this.deliveryType !== 'pickup') {
                    const hasSelectedAddr = this.selectedAddressId !== '' && this.selectedAddressId !== null;
                    const hasNewAddr = this.getValue(['city', 'city_m']) && this.getValue(['street', 'street_m']);
                    if (!hasSelectedAddr && !hasNewAddr) { e.address = 'Укажите адрес доставки'; valid = false; }
                }"""

new = """                if (this.deliveryType !== 'pickup') {
                    const hasSelectedAddr = this.selectedAddressId !== '' && this.selectedAddressId !== null;
                    if (!hasSelectedAddr) {
                        if (!this.getValue(['city', 'city_m'])) { e.address = 'Укажите город'; valid = false; }
                        else if (!this.getValue(['street', 'street_m'])) { e.address = 'Укажите улицу'; valid = false; }
                        else if (!this.getValue(['house', 'house_m'])) { e.address = 'Укажите номер дома'; valid = false; }
                        else if (!this.getValue(['postal_code', 'postal_code_m'])) { e.address = 'Укажите индекс'; valid = false; }
                    }
                }"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - frontend validation updated")
else:
    print("ERROR: old block not found")
