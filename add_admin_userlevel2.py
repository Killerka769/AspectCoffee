filepath = '/app/apps/users/admin.py'
with open(filepath, 'r') as f:
    content = f.read()

# Update import
old_import = 'from apps.users.models import User, Address, EmailLog, Achievement, UserAchievement, DiscountLevel, BonusTransaction'
new_import = 'from apps.users.models import User, Address, EmailLog, Achievement, UserAchievement, DiscountLevel, BonusTransaction, UserLevel'

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Add admin registration at end
    admin_code = '''

@admin.register(UserLevel)
class UserLevelAdmin(ModelAdmin):
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
    print('NOT FOUND')
    print('First 10 lines:', repr(content[:500]))
