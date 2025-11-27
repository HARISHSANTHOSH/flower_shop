from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import render
from flowerapp import models, serializers
from django.db.models import Q
from django.db import transaction
from .tasks import send_order_confirmation_email
from .pagination import FlowerPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)


class FlowerListCreateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        flowers = (
            models.Flower.objects.select_related("category").order_by("id")
        )

        search = request.GET.get("search")
        category_id = request.GET.get("category")

        if search:
            flowers = flowers.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

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
    return render(request, "login.html")
<<<<<<< Updated upstream
=======


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
>>>>>>> Stashed changes
