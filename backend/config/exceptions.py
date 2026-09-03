"""
Custom exception handler for consistent API error responses.
"""

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Return consistent JSON error format:
    {
        "success": false,
        "message": "...",
        "errors": {...}
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        errors = {}
        message = "Xatolik yuz berdi."

        if isinstance(response.data, dict):
            # Extract 'detail' key if present
            if "detail" in response.data:
                message = str(response.data["detail"])
            else:
                errors = response.data
                # Build a human-readable message from field errors
                first_error = None
                for _field, field_errors in response.data.items():
                    if isinstance(field_errors, list) and field_errors:
                        first_error = str(field_errors[0])
                        break
                    elif isinstance(field_errors, str):
                        first_error = field_errors
                        break
                if first_error:
                    message = first_error
        elif isinstance(response.data, list):
            message = str(response.data[0]) if response.data else message

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
        }

    return response
