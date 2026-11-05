from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from supportops.config import Settings
from supportops.database import check_database, create_database_engine
from supportops.integrations_api import router as integrations_router
from supportops.orders_api import router as orders_router
from supportops.policies_api import router as policies_router
from supportops.tickets_api import router as tickets_router


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(configuration)
        application.state.engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="SupportOps AI", version="0.1.0", lifespan=lifespan)
    application.state.settings = configuration
    application.include_router(orders_router)
    application.include_router(policies_router)
    application.include_router(tickets_router)
    application.include_router(integrations_router)

    @application.get("/api/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok", "service": "supportops-api"}

    @application.get("/api/health/ready")
    def ready(request: Request) -> JSONResponse:
        try:
            check_database(request.app.state.engine)
        except SQLAlchemyError:
            # Connection exceptions can contain credentials or host details.
            return JSONResponse({"status": "unavailable", "database": "unavailable"}, 503)
        return JSONResponse({"status": "ready", "database": "ready"})

    return application
