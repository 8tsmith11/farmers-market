from django.contrib import admin
from .models import Contract, Farm, CropType, InventoryItem, Plot

# Register your models here.
@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'balance']

@admin.register(CropType)
class CropTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'grow_time_seconds', 'base_price', 'seed_price']

@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'farm', 'x', 'y', 'crop_type', 'planted_at', 'harvest_ready_at']
    list_filter = ['farm']

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'farm', 'crop_type', 'quantity']
    list_filter = ['farm']

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['id', 'farm', 'crop_type', 'quantity_required', 'reward_coins', 'is_completed', 'expires_at']
    list_filter = ['farm']