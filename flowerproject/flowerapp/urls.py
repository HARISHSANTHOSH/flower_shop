from django.urls import path
from django.views.generic import TemplateView
from .views import FlowerListCreateAPIView, flower_page,LoginAPIView,BuyNowAPIView,SignupAPIView,signup_page,login_page,OrderListAPIView,admin_orders_page,MeView,OrderDetailAPIView,CartAPIView,CartItemAPIView,CustomerOrderListAPIView,CreatePaymentOrderAPIView,RazorpayWebhookAPIView


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
	path('api/v1/orders/<int:pk>/', OrderDetailAPIView.as_view()),
	path('api/v1/cart/',               CartAPIView.as_view()),
    path('api/v1/cart/<int:item_id>/', CartItemAPIView.as_view()),
	path('api/v1/my-orders/', CustomerOrderListAPIView.as_view()),
	path('orders/', TemplateView.as_view(template_name='orders.html'), name='orders'),
	path('api/v1/create-payment/', CreatePaymentOrderAPIView.as_view()),
	path('webhook/razorpay/',RazorpayWebhookAPIView.as_view(), name='razorpay-webhook'),
	
]

