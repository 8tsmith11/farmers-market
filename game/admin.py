from django.contrib import admin
from .models import Farm, CropType

# Register your models here.
@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'balance']

@admin.register(CropType)
class CropTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'grow_time_hours', 'base_price', 'seed_price']