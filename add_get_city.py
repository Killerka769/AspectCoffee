filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

old = '''    def get_level(self):'''
new = '''    def get_city(self):
        from apps.orders.models import Order
        last_order = Order.objects.filter(user=self).order_by("-created_at").first()
        if last_order and last_order.delivery_address:
            return last_order.delivery_address.get("city", "")
        return ""

    def get_level(self):'''

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
