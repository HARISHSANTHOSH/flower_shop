from django.contrib import admin
from django.db.models import Count
from flowerapp import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(models.Flower)
class FlowerAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'category']
    list_editable = ['price', 'stock']
    list_filter = ['category']
    search_fields = ['name', 'description']


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['username', 'phone_number', 'address', 'total_orders']
    search_fields = ['user__username', 'phone_number']

    def username(self, obj):
        return obj.user.username

    def total_orders(self, obj):
        return obj.orders.count()
    total_orders.short_description = 'Total Orders'


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_amount', 'created_at']
    list_filter = ['status']
    search_fields = ['customer__user__username']
    readonly_fields = ['created_at', 'order_date']


@admin.register(models.OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'flower', 'quantity', 'unit_price']
    search_fields = ['flower__name']


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user']
    search_fields = ['user__username']


@admin.register(models.Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['customer', 'created_at']

@admin.register(models.CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'flower', 'quantity']