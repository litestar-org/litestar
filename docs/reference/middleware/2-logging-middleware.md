# Logging Middleware

::: starlite.middleware.logging.LoggingMiddlewareConfig
    options:
        members:
            - exclude
            - exclude_opt_key
            - include_compressed_body
            - logger_name
            - middleware
            - middleware_class
            - request_cookies_to_obfuscate
            - request_headers_to_obfuscate
            - request_log_fields
            - request_log_message
            - response_cookies_to_obfuscate
            - response_headers_to_obfuscate
            - response_log_fields
            - response_log_message

::: starlite.middleware.logging.LoggingMiddleware
    options:
        members:
            - __init__
            - create_send_wrapper
            - extract_request_data
            - extract_response_data
            - log_message
            - log_request
            - log_response
