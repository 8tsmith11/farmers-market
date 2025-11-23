from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Create your models here.

class Farm(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farm')
    name = models.CharField(max_length=100)
    balance = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
class CropType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    grow_time_seconds = models.PositiveIntegerField()
    base_price = models.PositiveIntegerField()
    seed_price = models.PositiveIntegerField()

class Plot(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='plots')
    x = models.PositiveSmallIntegerField(default=0)
    y = models.PositiveSmallIntegerField(default=0)
    crop_type = models.ForeignKey(CropType, on_delete=models.SET_NULL, null=True, blank=True)
    planted_at = models.DateTimeField(null=True, blank=True)
    harvest_ready_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Plot ({self.x}, {self.y}) of {self.farm.name}"
    
    def is_ready(self):
        return (
            self.crop_type is not None and
            self.harvest_ready_at is not None and
            timezone.now() >= self.harvest_ready_at
        )
    
class InventoryItem(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='inventory')
    crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('farm', 'crop_type')

    def __str__(self):
        return f"{self.quantity} x {self.crop_type.name} on {self.farm.name}"
    
