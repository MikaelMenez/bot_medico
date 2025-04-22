from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from whatsapp.views import WhatsappApi

urlpatterns = [
    path('morecare/admin/', admin.site.urls),
    path("morecare/zap/", WhatsappApi.as_view(), name="zap"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
