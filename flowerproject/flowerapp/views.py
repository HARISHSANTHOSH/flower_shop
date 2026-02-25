# Django
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.db.models import Q, Sum, Prefetch
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

# DRF
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

# Third party
import json
import razorpay
import requests as python_requests


# Local
from flowerapp import models, serializers
from .serializers import SignupSerializer, LoginSerializer
from .permissions import IsSuperAdmin
from .pagination import FlowerPagination
from .paginator import AdminOrderPagination
from .tasks import send_order_confirmation_email,send_order_cancellation_email


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



class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response({'error': 'Token required'}, status=400)

        try:
            # ✅ verify token with Google using allauth
            google_response = python_requests.get(
                'https://www.googleapis.com/oauth2/v3/tokeninfo',
                params={'id_token': token}
            )
            idinfo = google_response.json()

            if 'error' in idinfo:
                return Response({'error': 'Invalid Google token'}, status=400)

            if idinfo.get('aud') != settings.GOOGLE_CLIENT_ID:
                return Response({'error': 'Token client mismatch'}, status=400)

            email    = idinfo.get('email')
            name     = idinfo.get('name', '')
            username = email.split('@')[0]

            # ✅ get or create user
            from django.contrib.auth.models import User
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': name,
                }
            )

            # ✅ generate JWT tokens same as normal login
            refresh = RefreshToken.for_user(user)

            return Response({
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
                'email':   email,
                'name':    name,
            })

        except Exception as e:
            return Response({'error': 'Google login failed'}, status=400)

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        print("username", username)
        password = serializer.validated_data['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # ✅ generate fresh JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "Login successful",
                "access":  str(refresh.access_token),  # ✅
                "refresh": str(refresh),                # ✅
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response({'error': 'Refresh token required'}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist() 
            return Response({'message': 'Logged out successfully'})
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=400)

def signup_page(request):
    return render(request, "signup.html")

class BuyNowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user        = request.user
        customer, _ = models.Customer.objects.get_or_create(user=user)

        address         = request.data.get('address')
        phone           = request.data.get('phone')
        flower_ids      = request.data.get('flowers', [])
        payment_method  = request.data.get('payment_method', 'cod')
        idempotency_key = request.data.get('idempotency_key')

        if address:
            customer.address = address
            customer.save(update_fields=['address'])
        if phone:
            customer.phone_number = phone
            customer.save(update_fields=['phone_number'])

        if not flower_ids:
            return Response({'error': 'No flowers found'}, status=400)
        if not idempotency_key:
            return Response({'error': 'Idempotency key required'}, status=400)
        if payment_method == 'online':
            return Response({'error': 'Use create-payment API for online orders'}, status=400)

        existing_order = models.Order.objects.filter(
            idempotency_key=idempotency_key,
            customer=customer
        ).first()

        if existing_order:
            return Response({
                'order_id':       existing_order.id,
                'total':          existing_order.total_amount,
                'status':         existing_order.status,
                'payment_status': existing_order.payment_status,  # ✅ fixed
                'payment_method': existing_order.payment_method,  # ✅ fixed
            })

        flowers    = models.Flower.objects.filter(id__in=flower_ids)
        flower_map = {f.id: f for f in flowers}

        total = sum(flower_map[fl_id].price for fl_id in flower_ids if fl_id in flower_map)

        # ✅ atomic + removed order.save()
        with transaction.atomic():
            order = models.Order.objects.create(
                customer=customer,
                payment_method='cod',
                status='confirmed',
                payment_status='pending',
                total_amount=total,
                idempotency_key=idempotency_key,
            )

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
            models.OrderItem.objects.bulk_create(items)
            models.CartItem.objects.filter(cart__customer=customer).delete()

            transaction.on_commit(
                lambda: send_order_confirmation_email.delay(order.id)
            )

        return Response({
            'order_id':       order.id,
            'total':          total,
            'status':         order.status,
            'payment_status': order.payment_status,  # ✅ consistent response
            'payment_method': order.payment_method,
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
        idempotency_key = request.data.get('idempotency_key')

        if not amount:
            return Response({'error': 'Amount required'}, status=400)
        if not flower_ids:
            return Response({'error': 'No flowers found'}, status=400)
        if not idempotency_key:
            return Response({'error': 'Idempotency key required'}, status=400)

        existing_order = models.Order.objects.filter(
            idempotency_key=idempotency_key,
            customer=customer
        ).first()
        if existing_order:
            return Response({
                'razorpay_order_id': existing_order.razorpay_order_id,
                'django_order_id':   existing_order.id,
                'amount':            int(float(existing_order.total_amount) * 100),
                'currency':          'INR',
                'key_id':            settings.RAZORPAY_KEY_ID,
                'payment_status':    existing_order.payment_status,
                'status':            existing_order.status,
            })

        flowers    = models.Flower.objects.filter(id__in=flower_ids)
        flower_map = {f.id: f for f in flowers}

        total = sum(flower_map[fl_id].price for fl_id in flower_ids if fl_id in flower_map)

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        payment_order = client.order.create({
            'amount':          int(float(total) * 100),
            'currency':        'INR',
            'payment_capture': 1
        })

        # ✅ wrapped in atomic — removed order.save()
        with transaction.atomic():
            order = models.Order.objects.create(
                customer=customer,
                payment_method='online',
                status='payment_pending',
                payment_status='pending',
                razorpay_order_id=payment_order['id'],
                total_amount=total,
                idempotency_key=idempotency_key,
            )

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
            models.OrderItem.objects.bulk_create(items)

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



class OrderCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        user     = request.user
        customer = get_object_or_404(models.Customer, user=user)

        order = get_object_or_404(
            models.Order,
            id=order_id,
            customer=customer
        )

        # ✅ only confirmed orders can be cancelled
        if order.status != 'confirmed':
            return Response({
                'error': f'Order cannot be cancelled. Current status: {order.status}'
            }, status=400)

        with transaction.atomic():
            # COD — just cancel
            if order.payment_method == 'cod':
                order.status = 'cancelled'
                order.save(update_fields=['status'])

            # Online — trigger Razorpay refund
            elif order.payment_method == 'online':
                if not order.razorpay_payment_id:
                    return Response({
                        'error': 'Payment ID not found, contact support'
                    }, status=400)

                try:
                    client = razorpay.Client(
                        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                    )
                    # amount in paise
                    refund = client.payment.refund(
                        order.razorpay_payment_id,
                        {'amount': int(float(order.total_amount) * 100)}
                    )

                    order.status         = 'cancelled'
                    order.payment_status = 'refunded'
                    order.save(update_fields=['status', 'payment_status'])

                except Exception as e:
                    return Response({
                        'error': 'Refund failed, please contact support'
                    }, status=400)

        # ✅ send cancellation email
        transaction.on_commit(
            lambda: send_order_cancellation_email.delay(order.id)
        )

        return Response({
            'message':        'Order cancelled successfully',
            'order_id':       order.id,
            'status':         order.status,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
        })