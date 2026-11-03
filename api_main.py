from __future__ import annotations

import uvicorn

from app.services.api_settings import ApiSettings


if __name__ == "__main__":
    settings = ApiSettings.from_environment()
    uvicorn.run(
        "app.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
