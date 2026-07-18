# Full-text search infrastructure:
#   * search_vector column (weighted tsvector) + GIN index
#   * Postgres trigger keeping it in sync on every INSERT/UPDATE — no
#     application code involved, so bulk_update/update_or_create all work
#   * pg_trgm extension + trigram indexes on title/company for fuzzy search
# Also syncs accumulated model drift (BigAutoField, db_index flags, index
# renames) so future makemigrations stay clean.

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models

# Weights: title=A, company=B, skills=B, description=C. The skills JSONB is
# cast to text — ["Python", "Django"] tokenizes into python/django lexemes.
# Description is capped so a pathological listing cannot overflow the
# 1MB tsvector limit.
CREATE_TRIGGER = """
CREATE OR REPLACE FUNCTION jobs_job_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.company, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.skills::text, '')), 'B') ||
        setweight(to_tsvector('english', left(coalesce(NEW.description, ''), 100000)), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS jobs_job_search_vector_trigger ON jobs_job;
CREATE TRIGGER jobs_job_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, company, skills, description
    ON jobs_job
    FOR EACH ROW EXECUTE FUNCTION jobs_job_search_vector_update();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS jobs_job_search_vector_trigger ON jobs_job;
DROP FUNCTION IF EXISTS jobs_job_search_vector_update();
"""

# Touching title fires the trigger for every existing row
BACKFILL = "UPDATE jobs_job SET title = title;"

CREATE_TRGM_INDEXES = """
CREATE INDEX IF NOT EXISTS jobs_job_title_trgm
    ON jobs_job USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS jobs_job_company_trgm
    ON jobs_job USING gin (company gin_trgm_ops);
"""

DROP_TRGM_INDEXES = """
DROP INDEX IF EXISTS jobs_job_title_trgm;
DROP INDEX IF EXISTS jobs_job_company_trgm;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_job_enrichment_fields'),
    ]

    operations = [
        TrigramExtension(),
        migrations.RenameIndex(
            model_name='job',
            new_name='jobs_job_quality_5d3c11_idx',
            old_name='jobs_job_quality_posted_idx',
        ),
        migrations.AddField(
            model_name='job',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='company',
            field=models.CharField(db_index=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='job',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='job',
            name='posted_at',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='source',
            field=models.CharField(db_index=True, max_length=50),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['-posted_at', 'title'], name='jobs_job_posted__0c9385_idx'),
        ),
        migrations.AddIndex(
            model_name='job',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='jobs_search_vector_gin'),
        ),
        migrations.RunSQL(CREATE_TRIGGER, reverse_sql=DROP_TRIGGER),
        migrations.RunSQL(BACKFILL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(CREATE_TRGM_INDEXES, reverse_sql=DROP_TRGM_INDEXES),
    ]
