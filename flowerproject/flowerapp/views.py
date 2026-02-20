from django.http import HttpResponse
from rest_framework.response import Response

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
        return Response({
            "username": request.user.username,
            "role": request.user.profile.role
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
    permission_classes=[IsAuthenticated]
    def post(self,request):
        user=request.user
        customer, created = models.Customer.objects.get_or_create(user=user)
        flower_ids=request.data.get("flowers",[])

        if not flower_ids:
            return Response("No flowers found")

        order=models.Order.objects.create(customer=customer)
        total=0

        for fl_id in flower_ids:
            flower=models.Flower.objects.get(id=fl_id)
            item= models.OrderItem.objects.create(
                order=order,
                flower=flower,
                quantity=1,
                unit_price=flower.price
            )
            total +=item.get_total_price()
            
        order.total_amount=total
        order.save()
        transaction.on_commit(
            lambda: send_order_confirmation_email.delay(order.id)
        )
        return Response({"order_id":order.id,"total":total,"status":order.status})


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

        allowed = ['pending', 'processing', 'delivered', 'cancelled']
        if not new_status or new_status.lower() not in allowed:
            return Response({'error': f'Invalid status. Choose from {allowed}'}, status=400)

        order.status = new_status.lower()
        order.save(update_fields=['status'])  # only updates status column, nothing else

        return Response({'id': order.id, 'status': order.status})