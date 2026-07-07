from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0005_alter_job_company_alter_job_location_alter_job_title_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='company_logo',
            field=models.URLField(blank=True, default='', max_length=2048),
        ),
        migrations.AddField(
            model_name='job',
            name='remote_type',
            field=models.CharField(db_index=True, default='Not Specified', max_length=20),
        ),
        migrations.AddField(
            model_name='job',
            name='employment_type',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='job',
            name='category',
            field=models.CharField(blank=True, db_index=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='job',
            name='summary',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='job',
            name='quality_score',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='job',
            name='salary_min_usd',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='salary_max_usd',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['-quality_score', '-posted_at'], name='jobs_job_quality_posted_idx'),
        ),
    ]
