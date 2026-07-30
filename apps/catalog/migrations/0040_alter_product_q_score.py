from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0039_recipestep_brew_graph_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='q_score',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Оценка Q-грейдера'),
        ),
    ]
