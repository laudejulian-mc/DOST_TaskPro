from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static


# Custom Error Handlers
def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)


def custom_403(request, exception):
    return render(request, '403.html', status=403)


handler404 = custom_404
handler500 = custom_500
handler403 = custom_403


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),  # Includes your app's URLs
    path('myapp/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)