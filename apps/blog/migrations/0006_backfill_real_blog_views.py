from django.db import migrations


def backfill_real_blog_views(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    BlogPostView = apps.get_model("blog", "BlogPostView")
    ArticleReadHistory = apps.get_model("blog", "ArticleReadHistory")

    for read in ArticleReadHistory.objects.all().iterator():
        view, created = BlogPostView.objects.get_or_create(
            post_id=read.post_id,
            visitor_key=f"user:{read.user_id}",
            defaults={
                "user_id": read.user_id,
                "session_key": "",
            },
        )
        update_fields = {"user_id": read.user_id}
        if created:
            update_fields.update(
                first_viewed_at=read.read_at,
                last_viewed_at=read.read_at,
            )
        BlogPostView.objects.filter(pk=view.pk).update(**update_fields)

    for post_id in BlogPost.objects.values_list("pk", flat=True).iterator():
        real_views = BlogPostView.objects.filter(post_id=post_id).count()
        BlogPost.objects.filter(pk=post_id).update(views_count=real_views)


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0005_blogpostview"),
    ]

    operations = [
        migrations.RunPython(backfill_real_blog_views, migrations.RunPython.noop),
    ]
