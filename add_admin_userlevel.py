filepath = '/app/apps/users/admin.py'
with open(filepath, 'r') as f:
    content = f.read()

# Add import if not present
if 'from .models import User, Address' in content:
    old = 'from .models import User, Address, Achievement, DiscountLevel, UserAchievement, BonusTransaction, EmailLog, PaymentTransaction'
    new = 'from .models import User, Address, Achievement, DiscountLevel, UserAchievement, BonusTransaction, EmailLog, PaymentTransaction, UserLevel'
    if old in content:
        content = content.replace(old, new)
    
    # Add admin registration at end
    admin_code = '''

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "min_orders", "min_spent", "icon", "color", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("sort_order", "min_orders")
'''
    content += admin_code
    
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND import')
    # Find the import line
    for line in content.split('\n'):
        if 'from .models import' in line:
            print('Found:', line)
