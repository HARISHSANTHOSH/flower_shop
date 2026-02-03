from django.urls import path
from .views import FlowerListCreateAPIView, flower_page,login_page,BuyNowAPIView,SignupAPIView,signup_page, AddToCartAPIView, ViewCartAPIView


urlpatterns = [
	path('api/v1/flowers/', FlowerListCreateAPIView.as_view()),
	path('flowers/', flower_page, name='flower_page'),
	path('login/', login_page, name='login_page'),
	path('api/buy-now/', BuyNowAPIView.as_view(), name='buy-now'),
	path('api/signup/', SignupAPIView.as_view(), name='signup'),
	path('signup/', signup_page, name='signup_page'),  
	path('api/add-to-cart/', AddToCartAPIView.as_view(), name='add-to-cart'),
	path('api/view-cart/', ViewCartAPIView.as_view(), name='view-cart'),
]

