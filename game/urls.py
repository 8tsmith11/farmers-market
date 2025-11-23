from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('farm/me/', views.farm_me, name='farm-me'),
    path('crop-types/', views.crop_type_list, name='crop-type-list'),
    path('plots/', views.plot_list, name='plot-list'),  
    path('plots/<int:plot_id>/plant/', views.plant, name='plant'),
    path('plots/<int:plot_id>/harvest/', views.harvest, name='harvest'),
    path('inventory/', views.inventory_list, name='inventory-list'),
    path('inventory/sell-npc', views.sell_npc, name='sell-npc'),
]