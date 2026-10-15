from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0007_alter_articlelike_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="ArticleBookmark"),
        migrations.DeleteModel(name="ArticleReadHistory"),
        migrations.DeleteModel(name="BlogSeriesVisit"),
    ]