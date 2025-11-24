from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

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

    def __str__(self):
        return self.name

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
    
    @property
    def remaining_time_display(self):
        if self.harvest_ready_at is None:
            return ''
        delta = self.harvest_ready_at - timezone.now()
        total = int(delta.total_seconds())
        if total <= 0:
            return 'Ready now'
        if total < 60:
            return f'{total}s'
        minutes = total // 60
        if total < 3600:
            return f'{minutes}m'
        hours = total // 3600
        return f'{hours}h'
    
class InventoryItem(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='inventory')
    crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('farm', 'crop_type')

    def __str__(self):
        return f"{self.quantity} x {self.crop_type.name} on {self.farm.name}"
    
class Contract(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='contracts')
    crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)
    quantity_required = models.PositiveIntegerField()
    reward_coins = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Contract for {self.quantity_required} x {self.crop_type.name} for {self.farm.name}"
    
    @property
    def is_completed(self):
        return self.completed_at is not None
    
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
    
    @property
    def is_active(self):
        return not self.is_completed and not self.is_expired
    
CONTRACT_DURATION_MINUTES = 10
def ensure_contracts_for_farm(farm, desired_count=3):
    now = timezone.now()
    Contract.objects.filter(farm=farm, expires_at__lte=now).delete()

    existing = Contract.objects.filter(
        farm=farm,
        expires_at__gt=now,
    ).order_by('created_at')

    if existing.count() >= desired_count:
        return existing[:desired_count]

    crop_types = list(CropType.objects.all())
    if not crop_types:
        return existing

    batch_expires_at = existing.first().expires_at if existing.exists() else now + timezone.timedelta(minutes=CONTRACT_DURATION_MINUTES)
    needed = max(0, desired_count - existing.count())

    for _ in range(needed):
        crop = random.choice(crop_types)
        quantity_required = random.randint(5, 20)
        reward_coins = quantity_required * crop.base_price

        Contract.objects.create(
            farm = farm,
            crop_type = crop,
            quantity_required = quantity_required,
            reward_coins = reward_coins,   
            expires_at = batch_expires_at,
        )

    return Contract.objects.filter(
        farm = farm,
        expires_at__gt=now,
    ).order_by('created_at')[:desired_count]