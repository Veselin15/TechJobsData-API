from rest_framework.pagination import PageNumberPagination


class JobPagination(PageNumberPagination):
    """20 results by default; clients may request up to 50 via ?page_size=."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
