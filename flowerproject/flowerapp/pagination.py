from rest_framework.pagination import PageNumberPagination


class FlowerPagination(PageNumberPagination):
    page_size = 10  # 10 items per page
    page_size_query_param = "page_size"  # Allow client to override
    max_page_size = 50  # Max allowed if client specifies


# First create the pagination class
class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50