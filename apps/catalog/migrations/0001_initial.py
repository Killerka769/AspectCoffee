
import ckeditor_uploader.fields
import django.core.validators
import django.db.models.deletion
import imagekit.models.fields
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = [
    ]
    operations = [
        migrations.CreateModel(
            name='BrewMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Способ приготовления')),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'verbose_name': 'Способ приготовления',
                'verbose_name_plural': 'Способы приготовления',
            },
        ),
        migrations.CreateModel(
            name='FlavorNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Вкусовая нотка')),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'verbose_name': 'Вкусовая нотка',
                'verbose_name_plural': 'Вкусовые нотки',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название')),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'verbose_name': 'Тег',
                'verbose_name_plural': 'Теги',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('slug', models.SlugField(max_length=200, unique=True, verbose_name='Slug')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('image', imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='categories/', verbose_name='Изображение')),
                ('seo_title', models.CharField(blank=True, max_length=255, verbose_name='SEO Title')),
                ('seo_description', models.TextField(blank=True, verbose_name='SEO Description')),
                ('h1', models.CharField(blank=True, max_length=255, verbose_name='H1')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='catalog.category', verbose_name='Родительская категория')),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Категории',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, verbose_name='Название')),
                ('slug', models.SlugField(max_length=300, unique=True, verbose_name='Slug')),
                ('description', ckeditor_uploader.fields.RichTextUploadingField(blank=True, verbose_name='Описание')),
                ('short_description', models.TextField(blank=True, max_length=500, verbose_name='Краткое описание')),
                ('roast_level', models.CharField(blank=True, choices=[('light', 'Светлая'), ('medium', 'Средняя'), ('dark', 'Тёмная'), ('espresso', 'Эспрессо')], max_length=20, verbose_name='Степень обжарки')),
                ('origin_country', models.CharField(blank=True, max_length=100, verbose_name='Страна происхождения')),
                ('composition', models.TextField(blank=True, verbose_name='Состав')),
                ('main_image', imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='products/', verbose_name='Главное фото')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('is_featured', models.BooleanField(default=False, verbose_name='Рекомендуем')),
                ('is_new', models.BooleanField(default=False, verbose_name='Новинка')),
                ('is_bestseller', models.BooleanField(default=False, verbose_name='Хит продаж')),
                ('in_stock', models.BooleanField(db_index=True, default=True, verbose_name='В наличии')),
                ('rating_avg', models.DecimalField(decimal_places=2, default=0, max_digits=3, verbose_name='Средний рейтинг')),
                ('reviews_count', models.PositiveIntegerField(default=0, verbose_name='Кол-во отзывов')),
                ('seo_title', models.CharField(blank=True, max_length=255, verbose_name='SEO Title')),
                ('seo_description', models.TextField(blank=True, verbose_name='SEO Description')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
                ('brew_methods', models.ManyToManyField(blank=True, to='catalog.brewmethod', verbose_name='Способы приготовления')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='catalog.category', verbose_name='Категория')),
                ('flavor_notes', models.ManyToManyField(blank=True, to='catalog.flavornote', verbose_name='Вкусовые нотки')),
                ('related_products', models.ManyToManyField(blank=True, to='catalog.product', verbose_name='Похожие товары')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', imagekit.models.fields.ProcessedImageField(upload_to='products/gallery/', verbose_name='Изображение')),
                ('alt', models.CharField(blank=True, max_length=255, verbose_name='Alt текст')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Фото товара',
                'verbose_name_plural': 'Фото товара',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.PositiveIntegerField(verbose_name='Вес (г)')),
                ('grind', models.CharField(choices=[('whole', 'В зёрнах'), ('fine', 'Мелкий'), ('medium', 'Средний'), ('coarse', 'Крупный')], default='whole', max_length=20, verbose_name='Помол')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('old_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Старая цена')),
                ('stock_qty', models.PositiveIntegerField(default=0, verbose_name='Остаток на складе')),
                ('sku', models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Артикул')),
                ('is_preorder', models.BooleanField(default=False, verbose_name='Предзаказ')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='catalog.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Вариант товара',
                'verbose_name_plural': 'Варианты товара',
                'ordering': ['weight', 'grind'],
            },
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, verbose_name='Название')),
                ('slug', models.SlugField(unique=True)),
                ('difficulty', models.CharField(choices=[('easy', 'Простой'), ('medium', 'Средний'), ('hard', 'Сложный')], default='medium', max_length=10, verbose_name='Сложность')),
                ('time_minutes', models.PositiveIntegerField(verbose_name='Время (мин)')),
                ('description', ckeditor_uploader.fields.RichTextUploadingField(blank=True, verbose_name='Описание')),
                ('ingredients', models.JSONField(default=list, verbose_name='Ингредиенты')),
                ('main_image', imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='recipes/', verbose_name='Главное изображение')),
                ('video_url', models.URLField(blank=True, verbose_name='Ссылка на видео')),
                ('is_published', models.BooleanField(default=False, verbose_name='Опубликован')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brew_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recipes', to='catalog.brewmethod', verbose_name='Способ приготовления')),
                ('products', models.ManyToManyField(blank=True, related_name='recipes', to='catalog.product', verbose_name='Подходящие товары')),
            ],
            options={
                'verbose_name': 'Рецепт',
                'verbose_name_plural': 'Рецепты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RecipeStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.PositiveSmallIntegerField(verbose_name='Номер шага')),
                ('description', models.TextField(verbose_name='Описание шага')),
                ('image', imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='recipes/steps/', verbose_name='Изображение шага')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='catalog.recipe', verbose_name='Рецепт')),
            ],
            options={
                'verbose_name': 'Шаг рецепта',
                'verbose_name_plural': 'Шаги рецепта',
                'ordering': ['step_number'],
            },
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_name', models.CharField(blank=True, max_length=200, verbose_name='Имя автора')),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Рейтинг')),
                ('text', models.TextField(verbose_name='Текст отзыва')),
                ('is_approved', models.BooleanField(db_index=True, default=False, verbose_name='Одобрен')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='catalog.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Отзыв',
                'verbose_name_plural': 'Отзывы',
                'ordering': ['-created_at'],
            },
        ),
    ]
