from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    Branch,
    BranchService,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
)

PUBLIC_SALON_MODELS = (
    Salon,
    Branch,
    BranchService,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
)


def invalidate_public_salon_cache(**_kwargs):
    cache.clear()


for model in PUBLIC_SALON_MODELS:
    receiver(post_save, sender=model)(invalidate_public_salon_cache)
    receiver(post_delete, sender=model)(invalidate_public_salon_cache)
