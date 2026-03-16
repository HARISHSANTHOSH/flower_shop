from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        # ✅ handle list (ValidationError) and dict both
        if isinstance(response.data, list):
            message = response.data[0]
        elif isinstance(response.data, dict):
            message = response.data.get('detail', 'Something went wrong')
        else:
            message = 'Something went wrong'

        return Response({
            "status": "error",
            "message": str(message),
            "data": None
        }, status=response.status_code)
    
    return Response({
        "status": "error",
        "message": "Internal server error",
        "data": None
    }, status=500)