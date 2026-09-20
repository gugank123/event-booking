from rest_framework.views import exception_handler as drf_exception_handler


def _first_message(data):
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        return _first_message(data[0])
    if isinstance(data, dict) and data:
        # Prefer non_field_errors / detail if present, else the first field's error
        for key in ("detail", "non_field_errors"):
            if key in data:
                return _first_message(data[key])
        first_key = next(iter(data))
        value = _first_message(data[first_key])
        # Prefix with the field name unless it's already a generic message
        if first_key not in ("detail", "non_field_errors"):
            return f"{first_key}: {value}" if not isinstance(data[first_key], str) else value
        return value
    return "Something went wrong."


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {"error": _first_message(response.data)}
    return response
