"""Entry point: python -m service"""

import uvicorn
from service.config import Settings

settings = Settings()
uvicorn.run(
    "service.app:create_app",
    factory=True,
    host=settings.host,
    port=settings.port,
    log_level=settings.log_level.lower(),
)
