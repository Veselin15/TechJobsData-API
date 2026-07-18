from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Main Pages ---
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('developers/', views.developer_guide, name='developer_guide'),
    path('insights/', views.insights, name='insights'),

    # --- Career Guides (editorial content) ---
    path('guides/', views.guide_list, name='guide_list'),
    path('guides/<slug:slug>/', views.guide_detail, name='guide_detail'),

    # --- Company & Legal Pages ---
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),

    # --- Job Board Features ---
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/suggest/', views.job_suggest, name='job_suggest'),
    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    path('toggle-save/<int:job_id>/', views.toggle_save_job, name='toggle_save_job'),
    path('subscribe/', views.subscribe_alert, name='subscribe_alert'),

    # --- Authentication ---
    # FIXED: Uses Django's built-in LoginView with your custom template
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('regenerate-key/', views.regenerate_api_key, name='regenerate_api_key'),

    # --- Password Reset Flow ---
    path('password-reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),

    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
]