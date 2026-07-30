# Generated migration for ArticleBookmark and ArticleReadHistory

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleBookmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='Добавлена')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='blog.blogpost', verbose_name='Статья')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='article_bookmarks', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Закладка статьи',
                'verbose_name_plural': 'Закладки статей',
                'ordering': ['-added_at'],
                'unique_together': {('user', 'post')},
            },
        ),
        migrations.CreateModel(
            name='ArticleReadHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(auto_now=True, verbose_name='Прочитано')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads', to='blog.blogpost', verbose_name='Статья')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='article_reads', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'История чтения',
                'verbose_name_plural': 'История чтения',
                'ordering': ['-read_at'],
                'unique_together': {('user', 'post')},
            },
        ),
    ]
