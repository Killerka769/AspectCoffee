from django.db import models
from django.urls import reverse
from django.conf import settings
from ckeditor.fields import RichTextField


class BlogCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Адрес в URL")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Категория блога"
        verbose_name_plural = "Категории блога"

    def __str__(self):
        return self.name


class BlogSeries(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Адрес в URL")
    image = models.ImageField(upload_to="blog/series/", verbose_name="Обложка")
    description = models.TextField(blank=True, verbose_name="Описание")
    reading_minutes = models.PositiveIntegerField(default=5, verbose_name="Время чтения, мин")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Серия статей"
        verbose_name_plural = "Серии статей"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog:index")


class BlogPost(models.Model):
    category = models.ForeignKey(
        BlogCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="posts", verbose_name="Категория"
    )
    title = models.CharField(max_length=500, verbose_name="Заголовок")
    slug = models.SlugField(max_length=500, unique=True, verbose_name="Адрес в URL")
    image = models.ImageField(upload_to="blog/", blank=True, verbose_name="Изображение")
    short_description = models.TextField(blank=True, verbose_name="Краткое описание")
    content = RichTextField(verbose_name="Содержание")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    is_featured = models.BooleanField(default=False, verbose_name="На главной")
    series = models.ManyToManyField(BlogSeries, through="BlogSeriesPost", related_name="posts", blank=True, verbose_name="Серии")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Статья блога"
        verbose_name_plural = "Статьи блога"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})


class BlogPostView(models.Model):
    """One real viewer per article.

    Authenticated visitors are identified by user id; guests by the Django
    session key. Repeated reloads update ``last_viewed_at`` but never create a
    second view for the same person/session.
    """

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="view_records",
        verbose_name="Статья",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="blog_post_views",
        null=True,
        blank=True,
        verbose_name="Пользователь",
    )
    visitor_key = models.CharField("Ключ посетителя", max_length=100)
    session_key = models.CharField("Ключ сессии", max_length=40, blank=True)
    first_viewed_at = models.DateTimeField("Первый просмотр", auto_now_add=True)
    last_viewed_at = models.DateTimeField("Последний просмотр", auto_now=True)

    class Meta:
        verbose_name = "Просмотр статьи"
        verbose_name_plural = "Просмотры статей"
        ordering = ["-last_viewed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("post", "visitor_key"),
                name="unique_blog_post_viewer",
            ),
        ]

    def __str__(self):
        viewer = self.user or f"Гость {self.session_key[:8]}"
        return f"{viewer} → {self.post}"


class BlogSeriesPost(models.Model):
    series = models.ForeignKey(BlogSeries, on_delete=models.CASCADE, related_name="series_items", verbose_name="Серия")
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="series_items", verbose_name="Статья")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок статьи")

    class Meta:
        verbose_name = "Статья в серии"
        verbose_name_plural = "Статьи в серии"
        unique_together = [("series", "post")]
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.series}: {self.post}"


class BlogSeriesVisit(models.Model):
    series = models.ForeignKey(BlogSeries, on_delete=models.CASCADE, related_name="visits", verbose_name="Серия")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blog_series_visits", verbose_name="Пользователь")
    visited_at = models.DateTimeField("Посещено", auto_now=True)

    class Meta:
        verbose_name = "Посещение серии статей"
        verbose_name_plural = "Посещения серий статей"
        unique_together = [("series", "user")]


class ArticleLike(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="likes", verbose_name="Статья")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blog_likes", verbose_name="Пользователь")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Отметка «нравится» у статьи"
        verbose_name_plural = "Отметки «нравится» у статей"
        unique_together = [("post", "user")]


class ArticleComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments", verbose_name="Статья")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blog_comments", verbose_name="Пользователь")
    text = models.TextField(max_length=2000, verbose_name="Комментарий")
    is_approved = models.BooleanField(default=True, verbose_name="Опубликован")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий к статье"
        verbose_name_plural = "Комментарии к статьям"
        ordering = ["created_at"]


class ArticleBookmark(models.Model):
    """User bookmarked (saved to favourites) a blog article."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="article_bookmarks", verbose_name="Пользователь",
    )
    post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE,
        related_name="bookmarks", verbose_name="Статья",
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлена")

    class Meta:
        verbose_name = "Закладка статьи"
        verbose_name_plural = "Закладки статей"
        unique_together = [("user", "post")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.user} → {self.post.title}"


class ArticleReadHistory(models.Model):
    """Track the last time a user visited a blog article."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="article_reads", verbose_name="Пользователь",
    )
    post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE,
        related_name="reads", verbose_name="Статья",
    )
    read_at = models.DateTimeField(auto_now=True, verbose_name="Прочитано")

    class Meta:
        verbose_name = "История чтения"
        verbose_name_plural = "История чтения"
        unique_together = [("user", "post")]
        ordering = ["-read_at"]

    def __str__(self):
        return f"{self.user} читал {self.post.title}"

