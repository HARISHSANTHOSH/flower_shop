from django.http import HttpResponse
from rest_framework.response import Response
import razorpay
import json
from django.conf import settings

from .permissions import IsSuperAdmin
from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import render
from flowerapp import models, serializers
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.db import transaction
from .tasks import send_order_confirmation_email
from .pagination import FlowerPagination
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer,LoginSerializer
from .paginator import AdminOrderPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)


class FlowerListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
	
    def get(self, request):
        flowers = (
            models.Flower.objects.select_related("category").order_by("id")
        )
        category_id = request.GET.get("category")
        price_range=request.GET.get('price')
        if price_range:
            try:
                min_price,max_price=price_range.split("-")
                min_price = int(min_price)
                max_price=int(max_price)

                if max_price:
                    flowers=flowers.filter(price__gte=min_price,price__lte=max_price)
                else:
                    flowers=flowers.filter(price__gte=min_price)
            except ValueError:
                pass


       

        if category_id:
            flowers = flowers.filter(category_id=category_id)
        paginator = FlowerPagination()
        result_page = paginator.paginate_queryset(flowers, request)
        serializer = serializers.FlowerSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
            serializer = serializers.FlowerSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def flower_page(request):
    categories = models.Category.objects.all().order_by("name")
    return render(request, "flowers.html", {"categories": categories})

def login_page(request):
    return render(request,"login.html")

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user     = request.user
        customer = models.Customer.objects.filter(user=user).first()
        profile  = models.Profile.objects.filter(user=user).first() 
        return Response({
            'username':     user.username,
            'email':        user.email,
            'role': profile.role,
            'phone_number': customer.phone_number if customer else '',
            'address':      customer.address      if customer else '',
        })

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        print("username",username)
        password = serializer.validated_data['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

def signup_page(request):
    return render(request, "signup.html")

class BuyNowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user     = request.user
        customer, _ = models.Customer.objects.get_or_create(user=user)

        address = request.data.get('address')
        phone   = request.data.get('phone')
        if address:
            customer.address = address
            customer.save(update_fields=['address'])
        if phone:
            customer.phone_number = phone
            customer.save(update_fields=['phone_number'])

        flower_ids     = request.data.get('flowers', [])
        payment_method = request.data.get('payment_method', 'cod')

        if not flower_ids:
            return Response({'error': 'No flowers found'}, status=400)

        # ✅ Online payment — order already created in CreatePaymentOrderAPIView
        # So BuyNowAPIView should only handle COD
        if payment_method == 'online':
            return Response({'error': 'Use create-payment API for online orders'}, status=400)

        # COD only from here
        order = models.Order.objects.create(
            customer=customer,
            payment_method='cod',
            status='confirmed',       # ✅ COD confirmed immediately
            payment_status='pending', # pays at delivery
        )

        flowers   = models.Flower.objects.filter(id__in=flower_ids)
        flower_map = {f.id: f for f in flowers}

        items = []
        total = 0

        for fl_id in flower_ids:
            flower = flower_map[fl_id]
            items.append(models.OrderItem(
                order=order,
                flower=flower,
                quantity=1,
                unit_price=flower.price
            ))
            total += flower.price

        # ✅ bulk create — one DB hit instead of N hits
        models.OrderItem.objects.bulk_create(items)

        order.total_amount = total
        order.save()
        models.CartItem.objects.filter(cart__customer=customer).delete()

        transaction.on_commit(
            lambda: send_order_confirmation_email.delay(order.id)
        )

        return Response({
            'order_id': order.id,
            'total':    total,
            'status':   order.status  # confirmed
        })


class SignupAPIView(APIView):
    serializer_class = SignupSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": {
                "username": user.username,
                "email": user.email,
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)   


class OrderListAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):

        queryset = models.Order.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=models.OrderItem.objects.select_related('flower')
            )
        ).select_related('customer')

       

        # -------- Filters --------

        customer = request.query_params.get('customer')
        status = request.query_params.get('status')
        flower_name = request.query_params.get('flower_name')

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        total_min = request.query_params.get('total_min')
        total_max = request.query_params.get('total_max')

        ordering = request.query_params.get('ordering', '-created_at')

        filters = Q()

        if customer:
            filters &= Q(customer__user__username__icontains=customer)

        if status:
            filters &= Q(status__iexact=status)

        if flower_name:
            filters &= Q(items__flower__name__icontains=flower_name)

        if date_from:
            filters &= Q(created_at__date__gte=date_from)

        if date_to:
            filters &= Q(created_at__date__lte=date_to)

        if total_min:
            filters &= Q(total_amount__gte=total_min)

        if total_max:
            filters &= Q(total_amount__lte=total_max)

        queryset = queryset.filter(filters).distinct()

        # Safe ordering whitelist
        allowed_ordering = [
            'created_at',
            '-created_at',
            'total_amount',
            '-total_amount'
        ]

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)

        # Pagination
        paginator = AdminOrderPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = serializers.OrderSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

        
def admin_orders_page(request):
    return render(request, 'admin_orders.html')



class OrderDetailAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def patch(self, request, pk):
        order = get_object_or_404(models.Order, pk=pk)

        new_status = request.data.get('status')

        allowed = [
            'payment_pending',
            'payment_failed',
            'confirmed',
            'processing',
            'shipped',
            'delivered',
            'cancelled',
            'refunded',
        ]
        if not new_status or new_status.lower() not in allowed:
            return Response({'error': f'Invalid status. Choose from {allowed}'}, status=400)

        order.status = new_status.lower()
        order.save(update_fields=['status'])  # only updates status column, nothing else

        return Response({'id': order.id, 'status': order.status})


class CartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_cart(self, request):
        customer = get_object_or_404(models.Customer, user=request.user)
        cart, _  = models.Cart.objects.get_or_create(customer=customer)
        return cart

    def get(self, request):
        cart       = self.get_cart(request)
        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        cart      = self.get_cart(request)
        flower_id = request.data.get('flower_id')
        quantity  = int(request.data.get('quantity', 1))

        if not flower_id:
            return Response({'error': 'flower_id is required'}, status=400)

        flower = get_object_or_404(models.Flower, pk=flower_id)

        existing_qty = 0
        existing_item = None
        try:
            existing_item = models.CartItem.objects.get(cart=cart, flower=flower)
            existing_qty  = existing_item.quantity
        except models.CartItem.DoesNotExist:
            pass

        # stock check against total (existing + new)
        total_qty = existing_qty + quantity
        if flower.stock < total_qty:
            return Response(
                {'error': f'Only {flower.stock} units available. You already have {existing_qty} in cart.'},
                status=400
            )

        # add or increment
        if existing_item:
            existing_item.quantity = total_qty
            existing_item.save(update_fields=['quantity'])
            created = False
        else:
            models.CartItem.objects.create(cart=cart, flower=flower, quantity=quantity)
            created = True

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=201 if created else 200)


class CartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_item(self, request, item_id):
        customer = get_object_or_404(models.Customer, user=request.user)
        cart     = get_object_or_404(models.Cart, customer=customer)
        return get_object_or_404(models.CartItem, pk=item_id, cart=cart)

    def patch(self, request, item_id):
        item     = self.get_item(request, item_id)
        quantity = request.data.get('quantity')

        if quantity is None:
            return Response({'error': 'quantity is required'}, status=400)

        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
            return Response({'message': 'Item removed'}, status=200)

        if item.flower.stock < quantity:
            return Response(
                {'error': f'Only {item.flower.stock} units available'},
                status=400
            )

        item.quantity = quantity
        item.save(update_fields=['quantity'])
        return Response(serializers.CartItemSerializer(item).data)

    def delete(self, request, item_id):
        item = self.get_item(request, item_id)
        item.delete()
        return Response({'message': 'Item removed'}, status=200)



class CustomerOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer = get_object_or_404(models.Customer, user=request.user)

        orders = models.Order.objects.filter(
            customer=customer
        ).prefetch_related(
            Prefetch('items', queryset=models.OrderItem.objects.select_related('flower'))
        ).order_by('-created_at')

        serializer = serializers.OrderSerializer(orders, many=True,context={'request': request})
        return Response(serializer.data)

class CreatePaymentOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user        = request.user
        customer, _ = models.Customer.objects.get_or_create(user=user)

        amount     = request.data.get('amount')
        flower_ids = request.data.get('flowers', [])

        if not amount:
            return Response({'error': 'Amount required'}, status=400)
        if not flower_ids:
            return Response({'error': 'No flowers found'}, status=400)

        # 1. Fetch all flowers in one query ✅
        flowers    = models.Flower.objects.filter(id__in=flower_ids)
        flower_map = {f.id: f for f in flowers}

        # 2. Calculate total from DB prices (not frontend amount — more secure) ✅
        total = sum(flower_map[fl_id].price for fl_id in flower_ids if fl_id in flower_map)

        # 3. Create Razorpay order
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        payment_order = client.order.create({
            'amount':          int(float(total) * 100),  # ✅ use DB total not frontend amount
            'currency':        'INR',
            'payment_capture': 1
        })

        # 4. Create Django Order
        order = models.Order.objects.create(
            customer=customer,
            payment_method='online',
            status='payment_pending',
            payment_status='pending',
            razorpay_order_id=payment_order['id'],
            total_amount=total,              # ✅ save DB total not frontend amount
        )

        # 5. Bulk create order items ✅
        items = []
        for fl_id in flower_ids:
            if fl_id in flower_map:
                flower = flower_map[fl_id]
                items.append(models.OrderItem(
                    order=order,
                    flower=flower,
                    quantity=1,
                    unit_price=flower.price
                ))
        models.OrderItem.objects.bulk_create(items)  # ✅ one DB hit

        order.save()  # ✅ save order after items created

        return Response({
            'razorpay_order_id': payment_order['id'],
            'django_order_id':   order.id,
            'amount':            payment_order['amount'],
            'currency':          'INR',
            'key_id':            settings.RAZORPAY_KEY_ID,
        })

class RazorpayWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        payload = request.body
        data    = json.loads(payload)
        event   = data.get('event')
        
        print("WEBHOOK EVENT:", event)

        if event == 'payment.captured':
            payment     = data['payload']['payment']['entity']
            rp_order_id = payment['order_id']

            try:
                order = models.Order.objects.get(razorpay_order_id=rp_order_id)
                order.status              = 'confirmed'
                order.payment_status      = 'paid'
                order.razorpay_payment_id = payment['id']
                order.save()
                models.CartItem.objects.filter(cart__customer=order.customer).delete()
                print("ORDER CONFIRMED:", order.id)

                transaction.on_commit(
                    lambda: send_order_confirmation_email.delay(order.id)
                )
            except models.Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=404)

        elif event == 'payment.failed':
            payment     = data['payload']['payment']['entity']
            rp_order_id = payment['order_id']

            try:
                order = models.Order.objects.get(razorpay_order_id=rp_order_id)
                order.status         = 'payment_failed'
                order.payment_status = 'failed'
                order.save()
                print("ORDER FAILED:", order.id)
            except models.Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=404)

        return Response({'status': 'ok'})