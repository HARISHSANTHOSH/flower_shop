from flowerapp import models
from rest_framework import serializers
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
	class Meta:
		model =models.Category
		fields= '__all__'

class FlowerSerializer(serializers.ModelSerializer):
	category = CategorySerializer(read_only=True)

	class Meta:
		model = models.Flower
		fields = ['id', 'name', 'description', 'price', 'category']
		read_only_fields = ['id']

class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model =User
		fields= ["id","username","email"]

class CustomerSerializer(serializers.ModelSerializer):
    # Nested representation of the linked User account
    user = UserSerializer(read_only=True) 

    class Meta:
        model = models.Customer
        fields = ['id', 'user', 'phone_number', 'address']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    # Use the FlowerSerializer (or a lighter version) for better readability
    flower_name = serializers.CharField(source='flower.name', read_only=True)

    class Meta:
        model = models.OrderItem
        # Note: We exclude 'order' here because it's defined by the parent OrderSerializer
        fields = ['flower', 'flower_name', 'quantity', 'unit_price'] 
        read_only_fields = ['unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True) 
    
    customer_username = serializers.CharField(source='customer.user.username', read_only=True)

    class Meta:
        model = models.Order
        fields = ['id', 'customer', 'customer_username', 'order_date', 'status', 'total_amount', 'delivery_address', 'items']
        read_only_fields = ['total_amount', 'order_date', 'customer'] # Customer is often set automatically on creation


		




