from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Farm
from .serializers import FarmSerializer

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