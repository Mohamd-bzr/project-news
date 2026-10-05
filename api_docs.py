"""OpenAPI / Swagger documentation for FreeBuff REST API."""

import json

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "FreeBuff API",
        "version": "1.0.0",
        "description": "Real-time financial news, sentiment, and technical analysis API",
    },
    "servers": [{"url": "/"}],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
        }
    },
    "security": [{"ApiKeyAuth": []}],
    "paths": {
        "/api/v1/health": {
            "get": {
                "summary": "Health check",
                "security": [],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/api/v1/assets": {
            "get": {
                "summary": "List all assets",
                "responses": {"200": {"description": "Asset list"}},
            }
        },
        "/api/v1/articles": {
            "get": {
                "summary": "Get articles",
                "parameters": [
                    {"name": "symbol", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                ],
                "responses": {"200": {"description": "Article list"}},
            }
        },
        "/api/v1/indicators/{symbol}": {
            "get": {
                "summary": "Technical indicators",
                "parameters": [
                    {"name": "symbol", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "tf", "in": "query", "schema": {"type": "string", "default": "1D"}},
                ],
                "responses": {"200": {"description": "Indicator data"}},
            }
        },
        "/api/v1/sentiment": {
            "get": {
                "summary": "Sentiment analysis",
                "parameters": [
                    {"name": "symbol", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "Sentiment data"}},
            }
        },
        "/api/v1/calendar": {
            "get": {
                "summary": "Economic calendar",
                "parameters": [
                    {"name": "days", "in": "query", "schema": {"type": "integer", "default": 7}},
                ],
                "responses": {"200": {"description": "Calendar events"}},
            }
        },
        "/api/v1/reports/{symbol}": {
            "get": {
                "summary": "Technical report",
                "parameters": [
                    {"name": "symbol", "in": "path", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "Report"}},
            }
        },
    },
}


def get_swagger_html() -> str:
    """Return standalone Swagger UI HTML page."""
    spec_json = json.dumps(OPENAPI_SPEC)
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>FreeBuff API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>body {{ margin: 0; padding: 0; background: #0a0a1a; }}</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    SwaggerUIBundle({{
        spec: {spec_json},
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: "StandaloneLayout"
    }});
    </script>
</body>
</html>"""
