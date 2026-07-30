import re

filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

new_model = '''

class UserLevel(models.Model):
    name = models.CharField("Название", max_length=100)
    min_orders = models.PositiveIntegerField("Минимум заказов", default=0)
    min_spent = models.DecimalField("Минимум потрачено (р)", max_digits=12, decimal_places=2, default=0)
    icon = models.CharField("Иконка", max_length=10, blank=True, help_text="Эмодзи или текст")
    color = models.CharField("Цвет", max_length=7, blank=True, help_text="HEX цвет, например #FF6B00")
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Уровень пользователя"
        verbose_name_plural = "Уровни пользователей"
        ordering = ["sort_order", "min_orders"]

    def __str__(self):
        return self.name
'''

# Check if UserLevel already exists
if 'class UserLevel' in content:
    print('ALREADY EXISTS')
else:
    # Find the last class definition and append after it
    content += new_model
    with open(filepath, 'w') as f:
        f.write(content)
    print('ADDED')
