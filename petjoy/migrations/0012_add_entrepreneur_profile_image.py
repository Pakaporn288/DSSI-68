from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('petjoy', '0011_add_owner_to_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='entrepreneur',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='entrepreneur_profiles/'),
        ),
    ]
