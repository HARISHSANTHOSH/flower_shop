from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from flowerapp import models,serializers
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly
)


class FlowerListCreateAPIView(APIView):
	permissions=[IsAdminUser]
	
	def get(self,request):
		flowers=models.Flower.objects.all().select_related('category')
		serializer=serializers.FlowerSerializer(flowers,many=True)

		return Response(serializer.data,status=status.HTTP_200_OK)

	def post(sef,request):
		serializer=serializers.FlowerSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)