filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

old = '        super().save(*args, **kwargs)\nclass Address(models.Model):'
new = '''        super().save(*args, **kwargs)

    def get_level(self):
        from django.db.models import Sum
        from apps.orders.models import Order
        qs = Order.objects.filter(user=self).exclude(status=Order.STATUS_CANCELLED)
        orders_count = qs.count()
        total_spent = qs.aggregate(t=Sum("total_amount"))["t"] or 0
        level = UserLevel.objects.filter(
            is_active=True,
            min_orders__lte=orders_count,
            min_spent__lte=total_spent,
        ).order_by("-sort_order", "-min_orders", "-min_spent").first()
        return level or UserLevel.objects.filter(is_active=True).order_by("sort_order", "min_orders").first()
class Address(models.Model):'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('ADDED')
else:
    print('NOT FOUND')
    # find save method and class Address
    idx = content.find("super().save")
    if idx >= 0:
        print("save found at", idx)
        print(repr(content[idx:idx+200]))
