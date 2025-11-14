# in skills_exchange/urls.py

from django.contrib import admin
# Make sure to import 'include'
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # This line includes all URLs from your 'ui' app (like login, signup, find_skills)
    path('', include('ui.urls')),

    # 👇 ======================= ADD THIS LINE ======================= 👇
    # This line tells Django to look inside core/urls.py for any URL
    # that starts with 'core/'. This makes 'create_skill_request' available.
    path('core/', include('core.urls')),
    # 👆 ============================================================= 👆

]

# This is good practice for serving media files (like profile pictures) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)