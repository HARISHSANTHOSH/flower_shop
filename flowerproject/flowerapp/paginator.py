from rest_framework.pagination import PageNumberPagination





class AdminOrderPagination(PageNumberPagination):
    page_size = 20 # default orders per page
    page_size_query_param = 'page_size'  # allow client to adjust
    max_page_size = 200  # limit for safety