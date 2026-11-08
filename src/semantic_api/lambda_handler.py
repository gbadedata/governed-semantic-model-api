"""AWS Lambda entry point (API Gateway HTTP API, payload format 2.0).

The app and its backend are built once per container, so the Secrets Manager read and the
Entra token are reused across warm invocations.
"""

from mangum import Mangum

from .app import create_app

handler = Mangum(create_app(), lifespan="off")
