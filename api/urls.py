from django.urls import path
from .views import nearest_hospital, send_alert, smart_emergency, sos, get_hospitals

urlpatterns = [
    path('sos/', sos),
    path('hospitals/', get_hospitals),
    path('alert/', send_alert),
    path('nearest/', nearest_hospital),
    path('smart/', smart_emergency),
]