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
    unlocked_crops = models.ManyToManyField('CropType', blank=True, related_name='farms_unlocked')

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

    unlocks_crop = models.ForeignKey(
        CropType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='unlocking_contracts',
    )
    
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
    
CONTRACT_DURATION_MINUTES = 5


def ensure_contracts_for_farm(farm, desired_count=3):
    from datetime import timedelta
    import random

    now = timezone.now()

    # Drop expired contracts
    Contract.objects.filter(farm=farm, expires_at__lte=now).delete()

    # Active contracts (include completed, just not expired)
    existing = Contract.objects.filter(
        farm=farm,
        expires_at__gt=now,
    ).order_by('created_at')

    if existing.count() >= desired_count:
        return existing[:desired_count]

    crop_types = list(CropType.objects.all())
    if not crop_types:
        return existing

    if existing.exists():
        batch_expires_at = existing.first().expires_at
    else:
        batch_expires_at = now + timedelta(minutes=CONTRACT_DURATION_MINUTES)

    needed = max(0, desired_count - existing.count())

    # Unlocked vs locked crops for this farm
    unlocked_qs = farm.unlocked_crops.all()
    unlocked_ids = set(unlocked_qs.values_list('id', flat=True))
    locked_crops = [c for c in crop_types if c.id not in unlocked_ids]

    # Track if there is already an unlock contract active to prevent more than one
    active_unlock_ids = set(
        existing.filter(unlocks_crop__isnull=False)
                .values_list('unlocks_crop_id', flat=True)
    )
    unlock_already_present = len(active_unlock_ids) > 0

    def pick_payment_crop():
        # Prefer crops the farm can actually plant
        if unlocked_qs.exists():
            return random.choice(list(unlocked_qs))
        return random.choice(crop_types)

    created_unlock_this_batch = False

    for _ in range(needed):
        create_unlock_contract = False
        target_crop = None

        # Locked crops that are not already targeted by an unlock contract
        available_unlock_targets = [
            c for c in locked_crops
            if c.id not in active_unlock_ids
        ]

        # Only allow a single unlock contract overall (existing or newly created)
        if not unlock_already_present and not created_unlock_this_batch:
            if available_unlock_targets and random.random() < 0.33:
                create_unlock_contract = True
                target_crop = random.choice(available_unlock_targets)
                active_unlock_ids.add(target_crop.id)
                created_unlock_this_batch = True
                unlock_already_present = True

        payment_crop = pick_payment_crop()
        quantity_required = random.randint(5, 20)
        reward_coins = quantity_required * payment_crop.base_price

        Contract.objects.create(
            farm=farm,
            crop_type=payment_crop,
            quantity_required=quantity_required,
            reward_coins=reward_coins,
            expires_at=batch_expires_at,
            unlocks_crop=target_crop if create_unlock_contract else None,
        )

    return Contract.objects.filter(
        farm=farm,
        expires_at__gt=now,
    ).order_by('created_at')[:desired_count]

GRID_SIZE = 5
def create_farm_for_user(user, custom_name=None):
    from django.utils.text import slugify

    # avoid duplicate farms
    if hasattr(user, "farm"):
        return user.farm

    farm = Farm.objects.create(
        user=user,
        name=custom_name or f"{user.username}'s Farm",
        balance=1,
    )

    # unlock Wheat if it exists
    try:
        wheat = CropType.objects.get(name="Wheat")
        farm.unlocked_crops.add(wheat)
    except CropType.DoesNotExist:
        pass

    # create full GRID_SIZE x GRID_SIZE plots
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            Plot.objects.create(farm=farm, x=x, y=y)

    return farm

class MarketListing(models.Model):
    seller = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='market_listings',
    )
    crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()  # coins per unit
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.quantity} {self.crop_type.name} @ {self.unit_price}c (seller={self.seller.name})'

    @property
    def is_open(self):
        return self.active and self.quantity > 0

