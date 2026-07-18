"""
Tests for the layered search engine (jobs.search).

These run against a real Postgres test database: the tsvector trigger from
migration 0007 fires on insert, so what's tested here is the actual
production search path, not a mock.
"""
from django.test import TestCase

from jobs.models import Job
from jobs.search import (
    complete_prefixes, correct_typos, expand_synonyms, search_jobs,
)


def make_job(title, *, company='TestCo', skills=None, description='',
             url=None, **extra):
    return Job.objects.create(
        title=title,
        company=company,
        url=url or f'https://example.test/{abs(hash(title + company))}',
        source='Test',
        skills=skills or [],
        description=description,
        **extra,
    )


class QueryRewritingTests(TestCase):
    """Pure-Python layers: no database needed."""

    def test_synonym_expansion(self):
        self.assertIn('javascript', expand_synonyms('js developer'))
        self.assertIn('kubernetes', expand_synonyms('k8s'))
        # Quoted phrases are left untouched
        self.assertEqual(expand_synonyms('"exact phrase"'), '"exact phrase"')

    def test_two_word_alias(self):
        self.assertIn('node.js', expand_synonyms('node js developer'))

    def test_typo_correction(self):
        self.assertEqual(correct_typos('pyton'), 'python')
        self.assertEqual(correct_typos('pyton develper'), 'python developer')
        self.assertIsNone(correct_typos('python'))  # nothing to fix

    def test_prefix_completion(self):
        self.assertEqual(complete_prefixes('javascr'), 'javascript')
        self.assertIsNone(complete_prefixes('python'))  # already complete


class SearchEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.python_job = make_job(
            'Senior Python Developer', skills=['Python', 'Django'],
            description='Strong Python and Django experience required.')
        cls.python_mention = make_job(
            'DevOps Engineer', skills=['Docker'],
            description='Occasionally you will touch Python scripts.')
        cls.java_job = make_job(
            'Java Backend Engineer', skills=['Java'],
            description='Java and Spring Boot backend services.')
        cls.js_job = make_job(
            'JavaScript Frontend Developer', skills=['JavaScript', 'React'],
            description='Modern JavaScript with React.')
        cls.go_job = make_job(
            'Platform Engineer', skills=['Go', 'Kubernetes'],
            description='Microservices written in Go on Kubernetes.')
        cls.tax_job = make_job(
            'Tax Advisor', company='Steuerkanzlei Schmidt',
            description='We go far for our clients. Ready to go? No tech.')

    def search(self, q):
        return search_jobs(Job.objects.all(), q)

    def test_java_does_not_match_javascript(self):
        result = self.search('java')
        titles = {j.title for j in result.queryset}
        self.assertIn('Java Backend Engineer', titles)
        self.assertNotIn('JavaScript Frontend Developer', titles)

    def test_js_synonym_finds_javascript(self):
        result = self.search('js')
        titles = {j.title for j in result.queryset}
        self.assertIn('JavaScript Frontend Developer', titles)

    def test_title_match_outranks_description_mention(self):
        result = self.search('python')
        ranked = list(result.queryset.order_by('-rank'))
        self.assertEqual(ranked[0].title, 'Senior Python Developer')
        # The description-only mention still matches, just lower
        self.assertIn(self.python_mention, ranked)

    def test_typo_is_corrected_and_reported(self):
        result = self.search('pyton')
        self.assertEqual(result.corrected_query, 'python')
        self.assertIn(self.python_job, result.queryset)

    def test_prefix_search_as_you_type(self):
        result = self.search('javascr')
        self.assertIn(self.js_job, result.queryset)

    def test_ambiguous_go_matches_skill_not_prose(self):
        """'go' must find Go jobs, not every listing containing the verb."""
        result = self.search('go')
        jobs = set(result.queryset)
        self.assertIn(self.go_job, jobs)
        self.assertNotIn(self.tax_job, jobs)

    def test_golang_alias_hits_go_jobs(self):
        result = self.search('golang')
        self.assertIn(self.go_job, result.queryset)

    def test_fuzzy_fallback_for_misspelled_company(self):
        result = self.search('Steuerkanzlei Schmid')
        self.assertIn(self.tax_job, result.queryset)

    def test_empty_query_returns_everything(self):
        result = self.search('')
        self.assertEqual(result.matched_with, 'none')
        self.assertEqual(result.queryset.count(), Job.objects.count())

    def test_nonsense_query_returns_empty_not_error(self):
        result = self.search('xqzwvkj')
        self.assertEqual(result.queryset.count(), 0)

    def test_multiword_query_requires_all_terms(self):
        result = self.search('senior python developer')
        self.assertIn(self.python_job, result.queryset)
        self.assertNotIn(self.java_job, result.queryset)
