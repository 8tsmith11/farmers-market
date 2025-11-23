from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Farm, CropType, Plot
from .serializers import FarmSerializer, CropTypeSerializer, PlotSerializer

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