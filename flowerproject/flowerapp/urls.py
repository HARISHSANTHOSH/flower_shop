from django.urls import path
from .views import FlowerListCreateAPIView, flower_page,LoginAPIView,BuyNowAPIView,SignupAPIView,signup_page,login_page,OrderListAPIView,admin_orders_page,MeView,OrderDetailAPIView


urlpatterns = [
	path('api/v1/flowers/', FlowerListCreateAPIView.as_view()),
	path('flowers/', flower_page, name='flower_page'),
	path('api/login/', LoginAPIView.as_view(), name='login_page'),
	path('api/me/', MeView.as_view()),
	path('api/buy-now/', BuyNowAPIView.as_view(), name='buy-now'),
	path('api/signup/', SignupAPIView.as_view(), name='signup'),
	path('signup/', signup_page, name='signup_page'), 
	path('signin/',login_page,name='signin') ,
	path('api/v1/orders/',OrderListAPIView.as_view(),name='orders'),
	path('admin/orders/', admin_orders_page, name='admin-orders-page'),
	path('api/v1/orders/<int:pk>/', OrderDetailAPIView.as_view())
	
]

