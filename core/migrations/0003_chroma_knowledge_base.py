from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_documentchunk")]

    operations = [
        migrations.AddField(
            model_name="projectfile",
            name="chunk_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.DeleteModel(name="DocumentChunk"),
    ]
