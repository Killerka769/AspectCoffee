import os

path = '/app/apps/catalog/admin.py'
with open(path, 'r') as f:
    content = f.read()

old = '        ("Корзина и оформление", {"fields": ("cart_guarantee_text", "repeat_order_text", "payment_timeout_minutes", "success_title", "success_message", "success_footer")}),' 

new = '        ("Корзина и оформление", {"fields": ("cart_guarantee_text", "repeat_order_text", "payment_timeout_minutes", "success_title", "success_message", "success_footer")}),'
# Already looks right, let me add a new section for email confirmation
old2 = '        ("Рецепты", {"fields": ("allow_recipe_without_order",)}),'

new2 = '        ("Подтверждение email", {"fields": ("email_confirmation_enabled",)}),\n        ("Рецепты", {"fields": ("allow_recipe_without_order",)}),'

if old2 in content:
    content = content.replace(old2, new2)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - added email_confirmation_enabled to admin fieldsets")
else:
    print("ERROR: recipes fieldset not found")
