
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_cartitem_grind_orderitem_grind'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cartitem',
            name='grind',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='grind',
        ),
    ]
