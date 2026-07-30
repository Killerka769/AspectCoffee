import os

path = '/app/apps/orders/views.py'
with open(path, 'r') as f:
    content = f.read()

old = """                    if org_name_val and not user_profile.company_name:
                        user_profile.company_name = org_name_val
                        changed = True
                    if org_inn_val and not user_profile.company_inn:
                        user_profile.company_inn = org_inn_val
                        changed = True"""

new = """                    if org_name_val:
                        user_profile.company_name = org_name_val
                        changed = True
                    if org_inn_val:
                        user_profile.company_inn = org_inn_val
                        changed = True"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - org data now always saves to profile")
else:
    print("ERROR: block not found!")
