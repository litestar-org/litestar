# OpenTelemetry

::: starlite.contrib.open_telemetry.OpenTelemetryConfig
    options:
        members:
            - client_request_hook_handler
            - client_response_hook_handler
            - exclude
            - exclude_opt_key
            - meter
            - meter_provider
            - scope_span_details_extractor
            - scopes
            - server_request_hook_handler
            - tracer_provider
            - middleware

::: starlite.contrib.open_telemetry.OpenTelemetryInstrumentationMiddleware
    options:
        members:
            - __init__

::: starlite.contrib.open_telemetry.get_route_details_from_scope
