# OpenTelemetry

::: starlite.contrib.opentelemetry.OpenTelemetryConfig
    options:
        members:
            - client_request_hook_handler
            - client_response_hook_handler
            - exclude
            - exclude_opt_key
            - exclude_urls_env_key
            - meter
            - meter_provider
            - middleware
            - scope_span_details_extractor
            - scopes
            - server_request_hook_handler
            - tracer_provider

::: starlite.contrib.opentelemetry.OpenTelemetryInstrumentationMiddleware
    options:
        members:
            - __init__

::: starlite.contrib.opentelemetry.get_route_details_from_scope
