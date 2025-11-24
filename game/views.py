from django.shortcuts import render, get_object_or_404, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout as auth_logout
from django.db.models import F

from .models import Contract, Farm, CropType, InventoryItem, MarketListing, Plot, create_farm_for_user, ensure_contracts_for_farm
from .serializers import ContractSerializer, FarmSerializer, CropTypeSerializer, InventoryItemSerializer, MarketListingSerializer, PlotSerializer

# Create your views here.

@api_view(['GET'])
def health_check(request): 
    return Response({'status': 'ok'})

def logout_view(request):
    auth_logout(request)
    return redirect('login')

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

    if farm.unlocked_crops.exists() and not farm.unlocked_crops.filter(id=crop_type.id).exists():
        return Response({'detail': 'Seed not unlocked'}, status=status.HTTP_403_FORBIDDEN)

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

GRID_SIZE = 5

@login_required
def home(request):
    try:
        farm = Farm.objects.get(user=request.user)
    except Farm.DoesNotExist:
        farm = create_farm_for_user(request.user)
    plots = farm.plots.all().order_by('y', 'x')
    inventory = farm.inventory.select_related('crop_type')
    crop_types = list(farm.unlocked_crops.all() or CropType.objects.all())
    contracts = ensure_contracts_for_farm(farm)

    plot_map = {(plot.x, plot.y): plot for plot in plots}
    grid = []
    for y in range(GRID_SIZE):
        row = []
        for x in range(GRID_SIZE):
            row.append(plot_map.get((x, y)))
        grid.append(row)

    contract_crop_ids = list(
        Contract.objects.filter(farm=farm, completed_at__isnull=True)
        .values_list('crop_type_id', flat=True)
        .distinct()
    )
    inventory_map = {item.crop_type_id: item.quantity for item in inventory}
    for crop in crop_types:
        crop.available_quantity = inventory_map.get(crop.id, 0)

    market_listings = MarketListing.objects.filter(
        active=True,
        quantity__gt=0,
        crop_type_id__in=contract_crop_ids,
    ).exclude(seller=farm).select_related('crop_type', 'seller').annotate(
        total_price=F('quantity') * F('unit_price')
    ).order_by('unit_price')

    context = {
        'farm': farm,
        'user': request.user,
        'grid': grid,
        'grid_size': GRID_SIZE,
        'inventory': inventory,
        'crop_types': crop_types,
        'contracts': contracts,
        'market_listings': market_listings,
        'contract_crop_ids': contract_crop_ids,
        'inventory_map': inventory_map,
    }
    return render(request, 'game/home.html', context)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contract_list(request):
    farm = Farm.objects.get(user=request.user)
    contracts = ensure_contracts_for_farm(farm)
    serializer = ContractSerializer(contracts, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_contract(request, contract_id):
    farm = Farm.objects.get(user=request.user)
    contract = get_object_or_404(Contract, id=contract_id, farm=farm)

    if contract.is_completed:
        return Response({'detail': 'Contract is already completed.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if contract.is_expired:
        return Response({'detail': 'Contract has expired.'}, status=status.HTTP_400_BAD_REQUEST)

    # check inventory
    item = InventoryItem.objects.filter(farm=farm, crop_type=contract.crop_type).first()

    if item is None or item.quantity < contract.quantity_required:
        return Response({'detail': 'Insufficient crops in inventory to complete contract.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # consume crops
    item.quantity -= contract.quantity_required
    item.save()

    # reward coins
    farm.balance += contract.reward_coins
    farm.save()

    # unlock crop if applicable
    if contract.unlocks_crop and not farm.unlocked_crops.filter(id=contract.unlocks_crop.id).exists():
        farm.unlocked_crops.add(contract.unlocks_crop)

    # mark completed
    contract.completed_at = timezone.now()
    contract.save()

    return Response({
        'farm': FarmSerializer(farm).data,
        'contract': ContractSerializer(contract).data,
    })

class SignUpForm(UserCreationForm):
    farm_name = forms.CharField(max_length=100, label='Farm name', required=True)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('farm_name',)

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            create_farm_for_user(user, custom_name=form.cleaned_data.get('farm_name'))
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def market_create_listing(request):
    farm = Farm.objects.get(user=request.user)

    if request.method == 'GET':
        contract_crop_ids = list(
            Contract.objects.filter(farm=farm, completed_at__isnull=True)
            .values_list('crop_type_id', flat=True)
            .distinct()
        )
        listings = MarketListing.objects.filter(
            active=True,
            quantity__gt=0,
            crop_type_id__in=contract_crop_ids,
        ).exclude(seller=farm).select_related('crop_type', 'seller').order_by('unit_price')
        serializer = MarketListingSerializer(listings, many=True)
        return Response(serializer.data)

    crop_type_id = request.data.get('crop_type_id')
    quantity = request.data.get('quantity')
    unit_price = request.data.get('unit_price')

    if crop_type_id is None or quantity is None or unit_price is None:
        return Response(
            {'detail': 'crop_type_id, quantity, and unit_price are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        quantity = int(quantity)
        unit_price = int(unit_price)
    except ValueError:
        return Response(
            {'detail': 'quantity and unit_price must be integers'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity <= 0 or unit_price <= 0:
        return Response(
            {'detail': 'quantity and unit_price must be positive'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    crop_type = get_object_or_404(CropType, id=crop_type_id)

    # check inventory
    item = InventoryItem.objects.filter(farm=farm, crop_type=crop_type).first()
    if item is None or item.quantity <= 0:
        return Response(
            {'detail': 'Not enough crop in inventory to create listing'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if quantity > item.quantity:
        quantity = item.quantity

    # lock items into listing: remove from inventory
    item.quantity -= quantity
    item.save()

    listing = MarketListing.objects.create(
        seller=farm,
        crop_type=crop_type,
        quantity=quantity,
        unit_price=unit_price,
        active=True,
    )

    return Response(MarketListingSerializer(listing).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def market_buy(request, listing_id):
    buyer_farm = Farm.objects.get(user=request.user)
    listing = get_object_or_404(MarketListing, id=listing_id, active=True)

    if listing.seller_id == buyer_farm.id:
        return Response({'detail': 'Cannot buy from your own listing'},
                        status=status.HTTP_400_BAD_REQUEST)

    if listing.quantity <= 0:
        return Response({'detail': 'Listing has no quantity left'},
                        status=status.HTTP_400_BAD_REQUEST)

    quantity = listing.quantity

    total_price = quantity * listing.unit_price

    if buyer_farm.balance < total_price:
        return Response({'detail': 'Not enough coins'},
                        status=status.HTTP_400_BAD_REQUEST)

    # transfer coins
    buyer_farm.balance -= total_price
    buyer_farm.save()

    seller_farm = listing.seller
    seller_farm.balance += total_price
    seller_farm.save()

    # move items to buyer
    item, _ = InventoryItem.objects.get_or_create(
        farm=buyer_farm,
        crop_type=listing.crop_type,
        defaults={'quantity': 0},
    )
    item.quantity += quantity
    item.save()

    # update listing
    listing.quantity = 0
    listing.active = False
    listing.save()

    return Response({
        'listing': MarketListingSerializer(listing).data,
        'buyer_farm': FarmSerializer(buyer_farm).data,
        'seller_farm': FarmSerializer(seller_farm).data,
    })
