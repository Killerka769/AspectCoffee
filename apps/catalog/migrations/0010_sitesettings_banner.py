# Bug 11 (SiteSettings) + Bug 6 (Banner)
import imagekit.models.fields
import imagekit.processors
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_parsersetting'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wholesale_url', models.URLField(default='https://aspectcoffee.ru/?utm_source=im', help_text='Внешняя ссылка на оптовый сайт', verbose_name='Оптовый сайт')),
                ('contact_phone', models.CharField(blank=True, default='+78003334980', max_length=32, verbose_name='Телефон')),
                ('contact_telegram', models.CharField(blank=True, default='', max_length=200, verbose_name='Telegram')),
                ('contact_whatsapp', models.CharField(blank=True, default='https://api.whatsapp.com/send?phone=79508382000', max_length=200, verbose_name='WhatsApp')),
                ('free_delivery_min', models.PositiveIntegerField(default=2500, verbose_name='Бесплатная доставка от (₽)')),
            ],
            options={
                'verbose_name': 'Настройки сайта',
                'verbose_name_plural': 'Настройки сайта',
            },
        ),
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('subtitle', models.CharField(blank=True, max_length=300, verbose_name='Подзаголовок')),
                ('image', imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='banners/', verbose_name='Изображение')),
                ('cta_text', models.CharField(blank=True, default='Купить', max_length=80, verbose_name='Текст кнопки')),
                ('cta_url', models.CharField(default='/catalog/', max_length=500, verbose_name='Ссылка кнопки')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Баннер',
                'verbose_name_plural': 'Баннеры',
                'ordering': ['order', '-created_at'],
            },
        ),
    ]
