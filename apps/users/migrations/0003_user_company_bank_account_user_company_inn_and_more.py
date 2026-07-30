
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_managers_alter_user_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='company_bank_account',
            field=models.CharField(blank=True, max_length=25, verbose_name='Расчётный счёт'),
        ),
        migrations.AddField(
            model_name='user',
            name='company_inn',
            field=models.CharField(blank=True, max_length=12, verbose_name='ИНН'),
        ),
        migrations.AddField(
            model_name='user',
            name='company_kpp',
            field=models.CharField(blank=True, max_length=9, verbose_name='КПП'),
        ),
        migrations.AddField(
            model_name='user',
            name='company_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Компания'),
        ),
        migrations.AddField(
            model_name='user',
            name='credit_limit',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Лимит кредита'),
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('customer', 'Розничный покупатель'), ('wholesale_customer', 'Оптовый покупатель'), ('warehouse_operator', 'Оператор склада')], db_index=True, default='customer', max_length=25, verbose_name='Роль'),
        ),
        migrations.AddField(
            model_name='user',
            name='wholesale_discount',
            field=models.PositiveIntegerField(default=0, help_text='Скидка от розничной цены для оптового покупателя', verbose_name='Оптовая скидка (%)'),
        ),
    ]
