from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': {
                'results': data,
                'pagination': {
                    'total': self.page.paginator.count,
                    'page': int(self.request.query_params.get('page', 1)),
                    'limit': int(self.request.query_params.get('limit', self.page_size)),
                    'pages': self.page.paginator.num_pages
                }
            }
        })