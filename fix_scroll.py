import os

# Fix 1: Basket edit address modal - remove scroll
basket_path = '/app/apps/orders/templates/orders/basket.html'
with open(basket_path, 'r') as f:
    content = f.read()

old_basket = 'max-width:480px;max-height:90vh;overflow-y:auto;'
new_basket = 'max-width:480px;'

if old_basket in content:
    content = content.replace(old_basket, new_basket)
    with open(basket_path, 'w') as f:
        f.write(content)
    print("OK - basket modal: removed scroll")
else:
    print("WARN: basket modal block not found")

# Fix 2: Profile address modal - remove scroll
profile_path = '/app/apps/users/templates/users/profile.html'
with open(profile_path, 'r') as f:
    content = f.read()

# Fix CSS rule for #address-modal
old_css = '#address-modal { display: none !important; position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important; width: 100vw !important; height: 100vh !important; background: rgba(0,0,0,0.75) !important; z-index: 99999 !important; align-items: center !important; justify-content: center !important; overflow-y: auto !important; padding: 1rem !important; }'
new_css = '#address-modal { display: none !important; position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important; width: 100vw !important; height: 100vh !important; background: rgba(0,0,0,0.75) !important; z-index: 99999 !important; align-items: center !important; justify-content: center !important; padding: 1rem !important; }'

if old_css in content:
    content = content.replace(old_css, new_css)
    print("OK - profile: removed overflow-y from #address-modal CSS")
else:
    print("WARN: profile #address-modal CSS not found")

# Fix the inner div
old_inner = 'max-h-[calc(100vh-2rem)] overflow-y-auto p-6 md:p-8 relative'
new_inner = 'p-6 md:p-8 relative'

if old_inner in content:
    content = content.replace(old_inner, new_inner)
    print("OK - profile: removed max-h and overflow-y from address modal inner div")
else:
    print("WARN: profile inner div not found")

with open(profile_path, 'w') as f:
    f.write(content)

print("Done")
