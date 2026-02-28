from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from rest_framework_api_key.models import APIKey

from .forms import RegisterForm  # Assuming you renamed your form or use the one from before
from .models import JobAlert, SavedJob, APIRequestLog
from jobs.models import Job

PLAN_DAILY_LIMITS = {
    "free": 20,
    "pro": 1000,
    "business": 10000,
}


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
    context['api_changelog_url'] = request.build_absolute_uri('/developers/changelog/')
    context['api_deprecation_url'] = request.build_absolute_uri('/developers/deprecation-policy/')

    if request.user.is_authenticated:
        sub = getattr(request.user, 'subscription', None)
        context['plan_type'] = sub.plan_type if sub else 'free'

        # Try to find an existing key to show the prefix
        # We use "user-{id}" naming convention for uniqueness
        api_key = APIKey.objects.filter(name=request.user.email).first()

        context['has_key'] = api_key is not None
        context['key_prefix'] = api_key.prefix if api_key else "YOUR_PREFIX"
    else:
        # Default placeholder for guests
        context['plan_type'] = 'free'
        context['has_key'] = False
        context['key_prefix'] = "YOUR_API_KEY"

    return render(request, 'core/developer_guide.html', context)


def api_changelog(request):
    return render(request, 'core/api_changelog.html')


def deprecation_policy(request):
    return render(request, 'core/deprecation_policy.html')


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

def job_list(request):
    """
    Searchable, paginated job board with 'Saved' status checking.
    """
    query = request.GET.get('q', '')
    location = request.GET.get('loc', '')

    jobs = Job.objects.all().order_by('-posted_at')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(skills__icontains=query) |
            Q(company__icontains=query)
        )
    if location:
        jobs = jobs.filter(location__icontains=location)

    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get IDs of jobs saved by this user (efficient lookup)
    saved_job_ids = []
    if request.user.is_authenticated:
        saved_job_ids = list(SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True))

    context = {
        'page_obj': page_obj,
        'query': query,
        'location': location,
        'saved_job_ids': saved_job_ids,
    }

    # If this is an HTMX request (pagination or search), render just the results
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
    # 1. Get Subscription Status
    sub = getattr(request.user, 'subscription', None)
    plan_type = sub.plan_type if sub else 'free'
    is_premium = plan_type in ['pro', 'business']
    daily_limit = PLAN_DAILY_LIMITS.get(plan_type, 20)

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

    # 6. Usage & Billing Transparency Metrics
    now = timezone.now()
    today = now.date()
    window_start = now - timedelta(days=6)

    usage_queryset = APIRequestLog.objects.filter(user=request.user)
    today_usage = usage_queryset.filter(created_at__date=today).count()
    remaining_quota = max(daily_limit - today_usage, 0)

    daily_usage_map = {
        item["day"]: item["count"]
        for item in usage_queryset.filter(created_at__gte=window_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    }

    daily_usage = []
    for days_back in range(6, -1, -1):
        day = today - timedelta(days=days_back)
        daily_usage.append({
            "label": day.strftime("%a"),
            "date": day.strftime("%Y-%m-%d"),
            "count": daily_usage_map.get(day, 0),
        })

    recent_requests = usage_queryset.order_by('-created_at')[:10]
    next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reset_in = next_reset - now

    context = {
        'api_key': api_key,
        'has_key': api_key is not None,
        'key_prefix': api_key.prefix if api_key else None,
        'plan_type': plan_type,
        'is_premium': is_premium,
        'saved_jobs': saved_jobs,
        'new_api_key': new_api_key,
        'daily_limit': daily_limit,
        'today_usage': today_usage,
        'remaining_quota': remaining_quota,
        'daily_usage': daily_usage,
        'recent_requests': recent_requests,
        'next_reset': next_reset,
        'reset_hours': reset_in.seconds // 3600,
        'reset_minutes': (reset_in.seconds % 3600) // 60,
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