from django import forms
from django.contrib import admin
from django.db import models

from find_primes.models import PrimeNumberRequests

# Register your models here.

@admin.register(PrimeNumberRequests)
class PrimeNumberRequestAdmin(admin.ModelAdmin):
    list_display = ("request_id", "no_of_primes", "status", "result", "completed_at")
    list_editable = ("result",)
    formfield_overrides = {
        models.TextField: {
            "widget": forms.Textarea(attrs={
                "cols": 40,
                "rows": 5,
            })
        }
    }

