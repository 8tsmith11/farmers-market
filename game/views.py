from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from .models import Farm, CropType, InventoryItem, Plot
from .serializers import FarmSerializer, CropTypeSerializer, InventoryItemSerializer, PlotSerializer

# Create your views here.

@api_view(['GET'])
def health_check(request): 
    return Response({'status': 'ok'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def farm_me(request):
    farm = Farm.objects.get(user=request.user)
    serializer = FarmSerializer(farm)
    return Response(serializer.data) 

@api_view(['GET'])
def crop_type_list(request):
    crops = CropType.objects.all()
    serializer = CropTypeSerializer(crops, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plot_list(request):
    farm = Farm.objects.get(user=request.user)
    plots = Plot.objects.filter(farm=farm).order_by('y', 'x')
    serializer = PlotSerializer(plots, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plant(request, plot_id):
    farm = Farm.objects.get(user=request.user)
    plot = get_object_or_404(Plot, id=plot_id, farm=farm)
    
    if plot.crop_type is not None:
        return Response({'detail': 'Plot is already planted.'}, status=status.HTTP_400_BAD_REQUEST)
    
    crop_type_id = request.data.get('crop_type_id')
    if crop_type_id is None:
        return Response({'detail': 'crop_type_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    crop_type = get_object_or_404(CropType, id=crop_type_id)

    if farm.balance < crop_type.seed_price:
        return Response({'detail': 'Insufficient funds to plant this crop.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # pay for seed
    farm.balance -= crop_type.seed_price
    farm.save()

    # plant crop
    now = timezone.now()
    plot.crop_type = crop_type
    plot.planted_at = now
    plot.harvest_ready_at = now + timedelta(seconds=crop_type.grow_time_seconds)
    plot.save()

    serializer = PlotSerializer(plot)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_list(request):
    farm = Farm.objects.get(user=request.user)
    items = farm.inventory.all()
    serializer = InventoryItemSerializer(items, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def harvest(request, plot_id):
    farm = Farm.objects.get(user=request.user)
    plot = get_object_or_404(Plot, id=plot_id, farm=farm)

    if not plot.is_ready():
        return Response({'detail': 'Crop is not ready for harvest.'}, status=status.HTTP_400_BAD_REQUEST)
    
    crop_type = plot.crop_type

    # add 1 of crop to inventory
    item, _ = InventoryItem.objects.get_or_create(farm=farm, crop_type=crop_type)
    item.quantity += 1
    item.save()

    # clear plot
    plot.crop_type = None
    plot.planted_at = None
    plot.harvest_ready_at = None
    plot.save()

    return Response({
        'plot': PlotSerializer(plot).data,
        'inventory_item': InventoryItemSerializer(item).data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sell_npc(request):
    farm = Farm.objects.get(user=request.user)
    crop_type_id = request.data.get('crop_type_id')
    quantity = request.data.get('quantity')

    if crop_type_id is None or quantity is None:
        return Response({'detail': 'crop_type_id and quantity are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        quantity = int(quantity)
    except ValueError:
        return Response({'detail': 'quantity must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
    if quantity <= 0:
        return Response({'detail': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)
    
    crop_type = get_object_or_404(CropType, id=crop_type_id)
    item = get_object_or_404(InventoryItem, farm=farm, crop_type=crop_type)

    if quantity > item.quantity:
        return Response({'detail': 'Insufficient quantity in inventory'}, status=status.HTTP_400_BAD_REQUEST)
    
    # update inventory
    item.quantity -= quantity
    item.save()

    # pay coins
    coins = quantity * crop_type.base_price
    farm.balance += coins
    farm.save()

    return Response({
        'earned_coins': coins,
        'balance': farm.balance,
        'inventory_item': InventoryItemSerializer(item).data,
    })

def home(request):
    return render(request, 'game/home.html')