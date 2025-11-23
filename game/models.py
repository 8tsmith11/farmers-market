from django.db import models
from django.contrib.auth import get_user_model

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
    grow_time_hours = models.PositiveIntegerField()
    base_price = models.PositiveIntegerField()
    seed_price = models.PositiveIntegerField()
