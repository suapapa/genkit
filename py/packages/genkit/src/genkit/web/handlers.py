# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Handlers for the Genkit web framework."""

import structlog

from genkit.web.responses import json_response
from genkit.web.typing import (
    HTTPScope,
    LifespanHandler,
    LifespanScope,
    Receive,
    Send,
)

logger = structlog.get_logger(__name__)


async def handle_not_found(
    scope: HTTPScope, receive: Receive, send: Send
) -> None:
    """Handle 404 not found responses.

    Args:
        scope: ASGI connection HTTP scope.
        receive: ASGI receive function.
        send: ASGI send function.
    """
    await send({
        'type': 'http.response.start',
        'status': 404,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'{"error": "Not Found"}',
    })


async def handle_health_check(
    scope: HTTPScope, receive: Receive, send: Send
) -> None:
    """Handle the health check GET endpoint.

    Args:
        scope: ASGI HTTP scope.
        receive: ASGI receive function.
        send: ASGI send function.
        query_params: Parsed query parameters.
    """
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'{"status": "ok"}',
    })


def create_lifespan_handler(
    on_lifespan_begin: LifespanHandler | None = None,
    on_lifespan_end: LifespanHandler | None = None,
) -> LifespanHandler:
    """Create a lifespan handler.

    Args:
        on_lifespan_begin: Lifespan handler for startup events.
        on_lifespan_end: Lifespan handler for shutdown events.

    Returns:
        Lifespan handler.
    """

    async def handle_lifespan(
        scope: LifespanScope, receive: Receive, send: Send
    ) -> None:
        """Handle ASGI lifespan events.

        Args:
            scope: ASGI connection lifespan scope.
            receive: ASGI receive function.
            send: ASGI send function.
        """
        while True:
            message = await receive()

            kind = message['type']
            match kind:
                case 'lifespan.startup':
                    if on_lifespan_begin:
                        try:
                            await logger.ainfo('lifespan startup')
                            await on_lifespan_begin(scope, receive, send)
                        except Exception as e:
                            await logger.aerror(
                                'lifespan startup failed', error=e
                            )
                            await send({
                                'type': 'lifespan.startup.failed',
                                'message': str(e),
                            })
                            return

                    await send({'type': 'lifespan.startup.complete'})
                case 'lifespan.shutdown':
                    if on_lifespan_end:
                        try:
                            await logger.ainfo('lifespan shutdown')
                            await on_lifespan_end(scope, receive, send)
                        except Exception as e:
                            await logger.aerror(
                                'lifespan shutdown failed', error=e
                            )
                            await send({
                                'type': 'lifespan.shutdown.failed',
                                'message': str(e),
                            })
                            return

                        await send({'type': 'lifespan.shutdown.complete'})
                    return
                case _:
                    await logger.error(f'Unsupported message type: {kind}')
                    await send({'type': 'lifespan.startup.complete'})
                    return

    return handle_lifespan
