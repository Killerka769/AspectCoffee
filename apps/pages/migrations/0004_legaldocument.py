from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0003_communitypost'),
    ]

    operations = [
        migrations.CreateModel(
            name='LegalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(
                    choices=[
                        ('public_offer', 'Публичная оферта'),
                        ('privacy', 'Политика конфиденциальности'),
                        ('user_agreement', 'Пользовательское соглашение'),
                        ('return_money', 'Возврат денег'),
                        ('shipment_and_payment', 'Доставка и оплата'),
                        ('cookies', 'Использование cookies'),
                    ],
                    help_text='Уникальный ключ документа. Используется в URL.',
                    max_length=64,
                    unique=True,
                    verbose_name='Идентификатор',
                )),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('meta_description', models.CharField(blank=True, max_length=300, verbose_name='Meta description (SEO)')),
                ('content', models.TextField(
                    help_text='HTML-разметка документа. Можно использовать заголовки h2-h3, списки, абзацы.',
                    verbose_name='Содержимое (HTML)',
                )),
                ('last_updated_label', models.CharField(
                    blank=True,
                    default='Дата последнего обновления: 1 января 2026 г.',
                    max_length=80,
                    verbose_name='Подпись даты обновления',
                )),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Юридический документ',
                'verbose_name_plural': 'Юридические документы',
                'ordering': ['slug'],
            },
        ),
    ]
