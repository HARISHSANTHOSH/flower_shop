from django.urls import path
from .views import FlowerListCreateAPIView, flower_page,login_page,BuyNowAPIView


urlpatterns = [
	path('api/v1/flowers/', FlowerListCreateAPIView.as_view()),
	path('flowers/', flower_page, name='flower_page'),
	path('login/', login_page, name='login_page'),
	path('api/buy-now/', BuyNowAPIView.as_view(), name='buy-now'),
	
]

