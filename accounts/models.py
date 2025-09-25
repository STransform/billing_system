from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    company_name = models.CharField("Company name", max_length=255, blank=True, null=True)
    address = models.TextField("Address", blank=True, null=True)
    phone_number = models.CharField("Phone number", max_length=50, blank=True, null=True)
    vat_number = models.CharField("VAT number", max_length=100, blank=True, null=True)
   
    def __str__(self):
        return self.get_full_name() or self.username