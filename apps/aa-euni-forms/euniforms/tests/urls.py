"""URLs for testing euniforms."""

from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('euniforms/', include('euniforms.urls')),
    path('accounts/login/', lambda request: None, name='login'),  # Mock login URL
]