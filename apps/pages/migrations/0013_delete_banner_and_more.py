from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0012_alter_communitypostbookmark_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="CommunityPostBookmark"),
        migrations.DeleteModel(name="CommunityPostDislike"),
        migrations.DeleteModel(name="CommunityPostRepost"),

        migrations.DeleteModel(name="Banner"),
        migrations.DeleteModel(name="SiteLink"),
    ]