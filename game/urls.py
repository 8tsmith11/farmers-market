from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('farm/me/', views.farm_me, name='farm_me'),
]