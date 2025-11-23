from rest_framework import serializers
from .models import Farm, CropType, Plot, InventoryItem

class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ['id', 'name', 'balance']

class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ['id', 'name', 'grow_time_seconds', 'base_price', 'seed_price']

class PlotSerializer(serializers.ModelSerializer):
    crop_type = CropTypeSerializer(read_only=True)

    class Meta:
        model = Plot
        fields = ['id', 'x', 'y', 'crop_type', 'planted_at', 'harvest_ready_at']

class InventoryItemSerializer(serializers.ModelSerializer):
    crop_type = CropTypeSerializer(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ['id', 'crop_type', 'quantity']