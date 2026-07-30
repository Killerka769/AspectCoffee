
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('catalog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='review',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviews', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(blank=True, to='catalog.tag', verbose_name='Теги'),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['slug'], name='catalog_cat_slug_695af4_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='productvariant',
            unique_together={('product', 'weight', 'grind')},
        ),
        migrations.AlterUniqueTogether(
            name='recipestep',
            unique_together={('recipe', 'step_number')},
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['product', 'is_approved'], name='catalog_rev_product_837d25_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['slug'], name='catalog_pro_slug_2b1eb6_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'is_active'], name='catalog_pro_categor_891fe8_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['created_at'], name='catalog_pro_created_92b554_idx'),
        ),
    ]
