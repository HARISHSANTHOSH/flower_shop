from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.



class Profile(models.Model):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('customer', 'Customer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# Signal to create/update Profile automatically
@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        # Create profile for new user
        Profile.objects.create(user=instance)
    else:
        # Save existing profile when User is updated
        if hasattr(instance, 'profile'):
            instance.profile.save()

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
    stock = models.PositiveIntegerField(default=0)
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
        ('payment_pending', 'Payment Pending'),  
        ('payment_failed',  'Payment Failed'),   
        ('confirmed',       'Confirmed'),        
        ('processing',      'Processing'),
        ('shipped',         'Shipped'),
        ('delivered',       'Delivered'),
        ('cancelled',       'Cancelled'),
        ('refunded',        'Refunded'),        
    )


    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    PAYMENT_METHOD_CHOICES = [
    ('cod',    'Cash on Delivery'),
    ('online', 'Online Payment'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
    ]

    payment_method      = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status      = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    razorpay_order_id   = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Referencing the choices using the class variable
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES, # <--- Used here
        default='Pending'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    created_at = models.DateTimeField(auto_now_add=True)
    # ... other fields
    class Meta:
        ordering = ['-created_at'] 
    
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
	

class Cart(models.Model):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.customer.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    flower = models.ForeignKey(
        Flower,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['cart', 'flower']  # same flower can't appear twice

    def get_total_price(self):
        return self.quantity * self.flower.price

    def __str__(self):
        return f"{self.quantity} x {self.flower.name}"