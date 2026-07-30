
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0005_roast_choices_and_parser_log'),
    ]
    operations = [
        migrations.CreateModel(
            name='ParseLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_slug', models.CharField(db_index=True, max_length=300, verbose_name='Slug товара')),
                ('status', models.CharField(choices=[('success', 'Успешно'), ('error', 'Ошибка'), ('skipped', 'Пропущено')], default='success', max_length=20, verbose_name='Статус')),
                ('message', models.TextField(blank=True, verbose_name='Сообщение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата')),
            ],
            options={
                'verbose_name': 'Лог парсинга',
                'verbose_name_plural': 'Логи парсинга',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['product_slug', 'status'], name='catalog_par_product_8c2f1b_idx')],
            },
        ),
    ]
