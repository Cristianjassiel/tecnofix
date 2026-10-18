"""Rutas del proyecto TecnoFix Dolores."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("servicios.urls")),
]

# En desarrollo, Django sirve las fotos de evidencia. En producción lo hace Nginx.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
