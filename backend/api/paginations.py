from rest_framework.pagination import PageNumberPagination

from backend.settings import REST_FRAMEWORK


class CustomPageNumberPagination(PageNumberPagination):

    page_size_query_param = 'limit'
    page_size = REST_FRAMEWORK['PAGE_SIZE']
