import os

path = '/app/apps/orders/views.py'
with open(path, 'r') as f:
    content = f.read()

# Fix backend validation - require city, street, house, postal_code
old_val = 'if delivery_type not in (Order.DELIVERY_PICKUP, *cdek_types) and (not city or not street) and not selected_address_id:\n                raise ValueError("Укажите адрес доставки")'

new_val = 'if delivery_type not in (Order.DELIVERY_PICKUP, *cdek_types) and not selected_address_id:\n                if not city:\n                    raise ValueError("Укажите город")\n                if not street:\n                    raise ValueError("Укажите улицу")\n                if not house:\n                    raise ValueError("Укажите номер дома")\n                if not postal_code:\n                    raise ValueError("Укажите индекс")'

if old_val in content:
    content = content.replace(old_val, new_val)
    print("OK - backend validation updated")
else:
    print("ERROR: old validation block not found")
    # Try to find it
    import re
    m = re.search(r'if delivery_type not in \(Order\.DELIVERY_PICKUP.*?raise ValueError\("Укажите адрес доставки"\)', content, re.DOTALL)
    if m:
        print(f"Found at pos {m.start()}: {m.group()[:100]}...")

with open(path, 'w') as f:
    f.write(content)

print("Done")
