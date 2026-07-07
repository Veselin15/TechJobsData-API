from collections import Counter
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from .forms import RegisterForm  # Assuming you renamed your form or use the one from before
from .models import JobAlert, SavedJob
from jobs.models import Job


# --- 1. Main Pages ---

def index(request):
    """The Landing Page (Public)"""
    job_count = Job.objects.count()
    return render(request, 'core/index.html', {'job_count': job_count})


def developer_guide(request):
    """Static page for API documentation."""
    context = {}

    # Generate the absolute API URL for the docs
    context['api_url'] = request.build_absolute_uri('/api/v1/jobs/')

    if request.user.is_authenticated:
        # Try to find an existing key to show the prefix
        # We use "user-{id}" naming convention for uniqueness
        api_key = APIKey.objects.filter(name=request.user.email).first()

        context['has_key'] = api_key is not None
        context['key_prefix'] = api_key.prefix if api_key else "YOUR_PREFIX"
    else:
        # Default placeholder for guests
        context['has_key'] = False
        context['key_prefix'] = "YOUR_API_KEY"

    return render(request, 'core/developer_guide.html', context)


def about(request):
    """About page: who we are and how the data is collected."""
    context = {
        'job_count': Job.objects.count(),
        'source_count': Job.objects.values('source').distinct().count(),
    }
    return render(request, 'core/about.html', context)


def contact(request):
    """Contact page with company details and support channels."""
    return render(request, 'core/contact.html')


def privacy(request):
    """Standalone, crawlable privacy policy."""
    return render(request, 'core/privacy.html')


def terms(request):
    """Standalone, crawlable terms of service."""
    return render(request, 'core/terms.html')


INSIGHTS_CACHE_KEY = 'market_insights_v1'
INSIGHTS_CACHE_TTL = 60 * 60  # 1 hour


def _build_insights():
    """Aggregate statistics computed from our own job database."""
    now = timezone.now()
    total_jobs = Job.objects.count()
    if total_jobs == 0:
        return None

    week_ago = now.date() - timedelta(days=7)
    new_this_week = Job.objects.filter(posted_at__gte=week_ago).count()

    # Skill demand: count every skill tag across all listings.
    skill_counter = Counter()
    for skills in Job.objects.exclude(skills=[]).values_list('skills', flat=True):
        skill_counter.update(s for s in skills if s)
    top_skills = skill_counter.most_common(15)
    max_skill_count = top_skills[0][1] if top_skills else 1
    top_skills = [
        {'name': name, 'count': count, 'pct': round(count * 100 / max_skill_count)}
        for name, count in top_skills
    ]

    # Salary transparency and averages by seniority (yearly, salaried posts only).
    with_salary = Job.objects.filter(Q(salary_min__isnull=False) | Q(salary_max__isnull=False))
    salary_share = round(with_salary.count() * 100 / total_jobs)
    # Averages use USD listings only — mixing currencies would skew the figures.
    salary_by_seniority = list(
        with_salary.filter(currency='USD')
        .exclude(seniority='Not Specified')
        .values('seniority')
        .annotate(avg_min=Avg('salary_min'), avg_max=Avg('salary_max'), n=Count('id'))
        .filter(n__gte=5)
        .order_by('-avg_max')
    )

    remote_share = round(
        Job.objects.filter(location__icontains='remote').count() * 100 / total_jobs
    )

    top_companies = list(
        Job.objects.exclude(company='')
        .values('company')
        .annotate(n=Count('id'))
        .order_by('-n')[:10]
    )

    by_source = list(
        Job.objects.values('source').annotate(n=Count('id')).order_by('-n')
    )
    max_source = by_source[0]['n'] if by_source else 1
    for row in by_source:
        row['pct'] = round(row['n'] * 100 / max_source)

    seniority_mix = list(
        Job.objects.exclude(seniority='Not Specified')
        .values('seniority')
        .annotate(n=Count('id'))
        .order_by('-n')
    )

    return {
        'total_jobs': total_jobs,
        'new_this_week': new_this_week,
        'top_skills': top_skills,
        'salary_share': salary_share,
        'salary_by_seniority': salary_by_seniority,
        'remote_share': remote_share,
        'top_companies': top_companies,
        'by_source': by_source,
        'seniority_mix': seniority_mix,
        'generated_at': now,
    }


def insights(request):
    """Tech job market insights computed from our aggregated dataset."""
    stats = cache.get(INSIGHTS_CACHE_KEY)
    if stats is None:
        stats = _build_insights()
        if stats is not None:
            cache.set(INSIGHTS_CACHE_KEY, stats, INSIGHTS_CACHE_TTL)
    return render(request, 'core/insights.html', {'stats': stats})


# --- 2. Authentication ---

def register(request):
    """Handles User Registration"""
    if request.method == 'POST':
        # Ensure you import the correct form class here
        # If your form is named 'EmailRequiredSignupForm', use that.
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully! Welcome to the dashboard.")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# --- 3. Job Board Logic ---

SALARY_OPTIONS = [
    (30000, '$30k+'),
    (50000, '$50k+'),
    (75000, '$75k+'),
    (100000, '$100k+'),
    (150000, '$150k+'),
]

DATE_OPTIONS = [
    (1, 'Last 24 hours'),
    (3, 'Last 3 days'),
    (7, 'Last week'),
    (14, 'Last 2 weeks'),
    (30, 'Last month'),
]

SORT_OPTIONS = [
    ('newest', 'Newest first'),
    ('oldest', 'Oldest first'),
    ('salary_high', 'Highest salary'),
    ('company', 'Company A–Z'),
]


def job_list(request):
    query = request.GET.get('q', '').strip()
    location = request.GET.get('loc', '').strip()
    source = request.GET.get('source', '')
    seniority = request.GET.get('seniority', '')
    min_salary = request.GET.get('min_salary', '')
    posted_within = request.GET.get('posted_within', '')
    remote_only = request.GET.get('remote') == '1'
    sort = request.GET.get('sort', 'newest')

    jobs = Job.objects.all()

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(skills__icontains=query) |
            Q(company__icontains=query)
        )
    if location:
        jobs = jobs.filter(location__icontains=location)
    if source:
        jobs = jobs.filter(source=source)
    if seniority:
        jobs = jobs.filter(seniority=seniority)
    if remote_only:
        jobs = jobs.filter(location__icontains='remote')
    if min_salary.isdigit():
        floor = int(min_salary)
        jobs = jobs.filter(Q(salary_min__gte=floor) | Q(salary_max__gte=floor))
    if posted_within.isdigit():
        cutoff = timezone.now().date() - timedelta(days=int(posted_within))
        jobs = jobs.filter(posted_at__gte=cutoff)

    if sort == 'oldest':
        jobs = jobs.order_by('posted_at', 'id')
    elif sort == 'salary_high':
        jobs = jobs.order_by(F('salary_max').desc(nulls_last=True),
                             F('salary_min').desc(nulls_last=True), '-posted_at')
    elif sort == 'company':
        jobs = jobs.order_by('company', '-posted_at')
    else:
        sort = 'newest'
        jobs = jobs.order_by('-posted_at', '-id')

    total_count = jobs.count()

    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    saved_job_ids = []
    if request.user.is_authenticated:
        saved_job_ids = list(SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True))

    available_sources = list(
        Job.objects.values_list('source', flat=True).distinct().order_by('source')
    )
    available_seniorities = list(
        Job.objects.exclude(seniority='Not Specified')
        .values_list('seniority', flat=True).distinct().order_by('seniority')
    )

    # Querystring with every active filter except 'page' — pagination links
    # append their own page number to it.
    params = request.GET.copy()
    params.pop('page', None)
    qs = params.urlencode()

    has_filters = any([source, seniority, min_salary, posted_within, remote_only]) \
        or sort != 'newest'

    context = {
        'page_obj': page_obj,
        'query': query,
        'location': location,
        'source': source,
        'seniority': seniority,
        'min_salary': min_salary,
        'posted_within': posted_within,
        'remote_only': remote_only,
        'sort': sort,
        'total_count': total_count,
        'saved_job_ids': saved_job_ids,
        'available_sources': available_sources,
        'available_seniorities': available_seniorities,
        'salary_options': SALARY_OPTIONS,
        'date_options': DATE_OPTIONS,
        'sort_options': SORT_OPTIONS,
        'qs': qs,
        'has_filters': has_filters,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'core/partials/job_results.html', context)

    return render(request, 'core/job_list.html', context)


def job_detail(request, pk):
    """SEO landing page for a single job."""
    job = get_object_or_404(Job, pk=pk)
    return render(request, 'core/job_detail.html', {'job': job})


# --- 4. User Dashboard & API Keys ---

@login_required
def dashboard(request):
    """
    The Money Page. Users manage their subscription and keys here.
    """
    try:
        sub = request.user.subscription
    except Exception:
        sub = None
    plan_type = sub.plan_type if sub else 'free'
    is_premium = plan_type in ['pro', 'business']

    # 2. Get Existing Key
    api_key = APIKey.objects.filter(name=request.user.email).first()

    # 3. Check for manually regenerated key
    new_api_key = request.session.pop('new_api_key', None)

    # 4. AUTO-GENERATE LOGIC (The Fix)
    # We add "and request.GET.get('success') != 'true'"
    # This prevents the key from being created during the "Syncing" reload.
    if is_premium and not api_key and request.GET.get('success') != 'true':
        api_key, key_string = APIKey.objects.create_key(name=request.user.email)
        new_api_key = key_string

    # 5. Get Saved Jobs
    saved_jobs = SavedJob.objects.filter(user=request.user).select_related('job').order_by('-created_at')

    context = {
        'api_key': api_key,
        'has_key': api_key is not None,
        'key_prefix': api_key.prefix if api_key else None,
        'is_premium': is_premium,
        'saved_jobs': saved_jobs,
        'new_api_key': new_api_key,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@require_POST
def regenerate_api_key(request):
    """
    Allows a user to revoke their old key and get a new one.
    """
    # Delete old key
    APIKey.objects.filter(name=request.user.email).delete()

    api_key, key_string = APIKey.objects.create_key(name=request.user.email)

    # --- THE FIX ---
    # Store the key in the session so the dashboard view can 'pop' it and show it to the user.
    request.session['new_api_key'] = key_string

    messages.success(request, "New API Key generated successfully!")
    return redirect('dashboard')


# --- 5. Interactive Features (HTMX) ---

@login_required
@require_POST
def toggle_save_job(request, job_id):
    """
    Toggles the saved state of a job.
    Called via HTMX.
    """
    job = get_object_or_404(Job, pk=job_id)
    saved_item, created = SavedJob.objects.get_or_create(user=request.user, job=job)

    if not created:
        # If it existed, delete it (Unsave)
        saved_item.delete()
        is_saved = False
    else:
        # It was just created (Save)
        is_saved = True

    # Render the button component with the new state
    return render(request, 'core/partials/save_icon.html', {'job': job, 'is_saved': is_saved})


@require_POST
def subscribe_alert(request):
    """
    Creates a JobAlert. This fixes the 'AttributeError'.
    """
    email = request.POST.get('email')
    keyword = request.POST.get('keyword') or 'all jobs'
    location = request.POST.get('location') or ''

    if email:
        JobAlert.objects.get_or_create(
            email=email,
            keyword=keyword,
            location=location
        )

    # Return a beautiful success message to replace the form
    return HttpResponse(f"""
        <div class="p-4 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-3 animate-fade-in-up">
            <div class="p-1.5 bg-green-500/20 rounded-full text-green-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            </div>
            <div>
                <p class="text-sm font-bold text-green-400">Alert Active!</p>
                <p class="text-xs text-green-300/70">We'll email you when new {keyword} jobs appear.</p>
            </div>
        </div>
    """)