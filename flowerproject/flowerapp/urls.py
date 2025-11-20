from django.urls import path
from .views import FlowerListCreateAPIView


urlpatterns = [
	path('api/v1/flowers/',FlowerListCreateAPIView.as_view())
]

