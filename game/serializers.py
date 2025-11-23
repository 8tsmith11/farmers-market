from rest_framework import serializers
from .models import Farm, CropType, Plot

class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ['id', 'name', 'balance']

class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ['id', 'name', 'grow_time_hours', 'base_price', 'seed_price']

class PlotSerializer(serializers.ModelSerializer):
    crop_type = CropTypeSerializer(read_only=True)

    class Meta:
        model = Plot
        fields = ['id', 'x', 'y', 'crop_type', 'planted_at', 'harvest_ready_at']