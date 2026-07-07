from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib.sitemaps.views import sitemap
from jobs.sitemaps import JobSitemap, StaticPagesSitemap
from django.views.generic import TemplateView

sitemaps = {
    'static': StaticPagesSitemap,
    'jobs': JobSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. The Core Frontend (Home & Dashboard)
    path('', include('core.urls')),

    # 2. Authentication (Login/Logout)
    path('accounts/', include('allauth.urls')),

    # 3. The Jobs API
    # (We mount this at 'api/', so it finds 'api/jobs/' and 'api/scrape/')
    path('api/', include('jobs.urls')),

    # 4. Payments API
    path('api/payments/', include('payments.urls')),

    # 5. Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('ads.txt', TemplateView.as_view(template_name="ads.txt", content_type="text/plain")),

]
