from flowerapp import models
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

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
        fields = ['id', 'customer', 'customer_username', 'order_date', 'status', 'total_amount', 'items']
        read_only_fields = ['total_amount', 'order_date', 'customer'] # Customer is often set automatically on creation


# serializers.py
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        # Optional: create a Customer object
        models.Customer.objects.create(user=user)
        return user



class CartItemSerializer(serializers.ModelSerializer):
    flower_name  = serializers.CharField(source='flower.name', read_only=True)
    flower_image = serializers.ImageField(source='flower.image', read_only=True)
    unit_price   = serializers.DecimalField(source='flower.price', max_digits=10, decimal_places=2, read_only=True)
    total_price  = serializers.SerializerMethodField()

    class Meta:
        model  = models.CartItem
        fields = ['id', 'flower', 'flower_name', 'flower_image', 'unit_price', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()


class CartSerializer(serializers.ModelSerializer):
    items       = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model  = models.Cart
        fields = ['id', 'items', 'grand_total']

    def get_grand_total(self, obj):
        return sum(item.get_total_price() for item in obj.items.all())