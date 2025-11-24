from rest_framework import serializers
from .models import Contract, Farm, CropType, MarketListing, Plot, InventoryItem

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

class ContractSerializer(serializers.ModelSerializer):
    crop_type = CropTypeSerializer(read_only=True)
    unlocks_crop = CropTypeSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 
            'crop_type', 
            'quantity_required', 
            'reward_coins', 
            'created_at',
            'expires_at', 
            'unlocks_crop',
            'is_active',
            'is_completed',
        ]
        
    def get_is_active(self, obj):
        return obj.is_active
    def get_is_completed(self, obj):
        return obj.is_completed

class MarketListingSerializer(serializers.ModelSerializer):
    crop_type = CropTypeSerializer(read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)

    class Meta:
        model = MarketListing
        fields = [
            'id',
            'seller_name',
            'crop_type',
            'quantity',
            'unit_price',
            'active',
            'created_at',
        ]
