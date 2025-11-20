from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Category(models.Model):
	name=models.CharField(max_length=100)
	descrition=models.CharField(max_length=200)

	def __str__(self):
		return self.name

class Flower(models.Model):
	name = models.CharField(max_length=100)
	description = models.CharField(max_length=200)
	price = models.DecimalField(
        max_digits=10,      
        decimal_places=2,    
        default=0.00         
    )
	image = models.ImageField(
        upload_to='flowers/', 
        blank=True,           
        null=True            
    )
	category = models.ForeignKey(
		Category,
		on_delete=models.SET_NULL,
		related_name='flowers',
		null=True
	)

	def __str__(self):
		return self.name

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField()

    def __str__(self):
        return self.user.username

class Order(models.Model):
    # Defining choices within the model class
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    
    # Referencing the choices using the class variable
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES, # <--- Used here
        default='Pending'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    # ... other fields
    
    def __str__(self):
        return f"Order #{self.id} - {self.status}"

class OrderItem(models.Model):
    # Foreign Key linking this item to its parent order
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Foreign Key linking the item to the specific flower product
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE)
    
    quantity = models.IntegerField(default=1)
    
    # Capture the price at the time of the order to protect against price changes
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) 
    
    def get_total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.flower.name}"
	
