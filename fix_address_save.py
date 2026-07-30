import os

path = '/app/apps/orders/views.py'
with open(path, 'r') as f:
    content = f.read()

# Fix address saving: include house, postal_code, is_default; use update logic
old = """                if city and street and not selected_address_id:
                    Address.objects.get_or_create(
                        user=request.user,
                        city=city,
                        street=street,
                        apartment=apartment,
                        defaults={"label": ""}
                    )"""

new = """                if city and street and not selected_address_id:
                    if is_address_main:
                        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                    addr_obj, _ = Address.objects.update_or_create(
                        user=request.user,
                        city=city,
                        street=street,
                        defaults={
                            "house": house,
                            "apartment": apartment,
                            "postal_code": postal_code,
                            "is_default": is_address_main,
                        }
                    )"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - address save: added house, postal_code, is_default")
else:
    print("ERROR: old block not found")

print("Done")
