from django.contrib import admin
from flowerapp import models
# Register your models here.
admin.site.register(models.Flower)
admin.site.register(models.Category)
admin.site.register(models.Customer)
admin.site.register(models.Order)
admin.site.register(models.OrderItem)