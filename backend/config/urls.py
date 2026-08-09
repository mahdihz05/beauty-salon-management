from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/auth/", include("accounts.urls")),
    path("api/management/", include("salons.urls")),
    path("api/admin-panel/", include("salons.admin_urls")),
    path("api/public/", include("salons.public_urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/reports/", include("reporting.urls")),
    path("api/support/", include("core.support_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA_FILES:
    urlpatterns += [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]

if (settings.FRONTEND_DIST / "index.html").exists():
    urlpatterns += [
        path("", TemplateView.as_view(template_name="index.html"), name="frontend-home"),
        re_path(
            r"^(?!api/|admin/|media/|static/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="frontend-spa",
        ),
    ]
