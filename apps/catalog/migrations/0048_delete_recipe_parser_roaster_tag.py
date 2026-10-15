from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0047_clear_accessory_taste_defaults"),
    ]

    operations = [
        migrations.DeleteModel(name="RecipeStep"),
        migrations.DeleteModel(name="Recipe"),

        migrations.DeleteModel(name="Roaster"),
        migrations.DeleteModel(name="Tag"),
        migrations.DeleteModel(name="ParserLog"),
        migrations.DeleteModel(name="ParserSetting"),

        migrations.RemoveField(model_name="product", name="roaster"),
        migrations.RemoveField(model_name="product", name="tags"),
        migrations.RemoveField(model_name="product", name="roaster_machine"),

        migrations.RemoveField(model_name="sitesettings", name="wholesale_url"),
        migrations.RemoveField(model_name="sitesettings", name="main_site_url"),
        migrations.RemoveField(model_name="sitesettings", name="roast_banner_is_active"),
        migrations.RemoveField(model_name="sitesettings", name="roast_banner_title"),
        migrations.RemoveField(model_name="sitesettings", name="roast_banner_subtitle"),
        migrations.RemoveField(model_name="sitesettings", name="openness_title"),
        migrations.RemoveField(model_name="sitesettings", name="openness_description"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_1_title"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_1_url"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_1_image"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_2_title"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_2_url"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_2_image"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_3_title"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_3_url"),
        migrations.RemoveField(model_name="sitesettings", name="openness_stream_3_image"),
    ]