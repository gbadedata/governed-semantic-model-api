"""FastAPI application: approved metric endpoints over the semantic backend."""

import re
import time
import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import __version__
from .backends.base import BackendError, ConfigError, DateRange, SemanticBackend
from .config import Settings, get_settings
from .logging_config import configure_logging
from .measures import CATALOGUE, CURRENCY, DATE_FILTERS, TOP_PRODUCTS_FILTERS, TOTAL_REVENUE

SERVICE = "governed-semantic-model-api"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


# ---------------- response models ----------------
class Period(BaseModel):
    start_date: date
    end_date: date


class Health(BaseModel):
    status: str
    service: str
    version: str
    backend: str
    upstream: str
    timestamp: datetime


class MeasureInfo(BaseModel):
    key: str
    semantic_model_measure: str
    definition: str


class RevenueResponse(BaseModel):
    period: Period
    currency: str
    total_revenue: float
    total_orders: int
    average_order_value: float | None
    source: str
    generated_at: datetime


class CategoryRow(BaseModel):
    category: str
    revenue: float


class CategoryResponse(BaseModel):
    period: Period
    currency: str
    measure: str
    categories: list[CategoryRow]
    source: str
    generated_at: datetime


class ProductRow(BaseModel):
    rank: int
    product_id: str
    product_name: str
    category: str
    revenue: float


class TopProductsResponse(BaseModel):
    period: Period
    currency: str
    measure: str
    limit: int
    products: list[ProductRow]
    source: str
    generated_at: datetime


# ---------------- errors ----------------
class InvalidRequest(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _error(request: Request, status: int, code: str, message: str, details=None, headers=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body, headers=headers)


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


# ---------------- backend wiring ----------------
def build_backend(settings: Settings) -> SemanticBackend:
    if settings.backend == "local":
        try:
            from .backends.local import LocalBackend
        except ImportError as exc:
            raise ConfigError("the local backend needs DuckDB: pip install '.[local]'") from exc
        return LocalBackend(settings.sample_data_dir)
    from .backends.fabric import FabricBackend
    from .secrets import load_fabric_credentials

    if not (settings.fabric_workspace_id and settings.fabric_dataset_id):
        raise ConfigError("set SEMANTIC_API_FABRIC_WORKSPACE_ID and SEMANTIC_API_FABRIC_DATASET_ID")
    return FabricBackend(
        settings.fabric_workspace_id,
        settings.fabric_dataset_id,
        load_fabric_credentials(settings),
        timeout=settings.fabric_timeout_seconds,
    )


def create_app(settings: Settings | None = None, backend: SemanticBackend | None = None) -> FastAPI:
    settings = settings or get_settings()
    logger = configure_logging(settings.log_level)
    backend = backend or build_backend(settings)  # fail fast on misconfiguration at cold start

    app = FastAPI(
        title="Governed Semantic Model API",
        version=__version__,
        description="Approved business metrics served from the governed semantic model. "
        "Only catalogued measures and approved filters are available.",
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        aws_id = request.scope.get("aws.event", {}).get("requestContext", {}).get("requestId")
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = aws_id or (supplied if _SAFE_REQUEST_ID.match(supplied) else uuid.uuid4().hex)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "request",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "backend": backend.name,
            },
        )
        return response

    @app.exception_handler(BackendError)
    async def backend_error(request: Request, exc: BackendError):
        logger.warning("upstream_error", extra={"request_id": request.state.request_id, "code": exc.code,
                                                "detail": str(exc)})
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return _error(request, exc.status_code, exc.code, "The semantic model could not answer this request.",
                      headers=headers)

    @app.exception_handler(InvalidRequest)
    async def invalid_request(request: Request, exc: InvalidRequest):
        return _error(request, exc.status_code, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return _error(request, 422, "invalid_request", "One or more query parameters are invalid.", details)

    # ---------------- dependencies ----------------
    def only(allowed: frozenset[str]):
        def check(request: Request) -> None:
            unknown = sorted(set(request.query_params) - allowed)
            if unknown:
                raise InvalidRequest(
                    f"unsupported query parameter(s): {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed))}.",
                    status_code=400,
                )
        return check

    def period(
        start_date: Annotated[date, Query(description="First order date included (YYYY-MM-DD)")],
        end_date: Annotated[date, Query(description="Last order date included (YYYY-MM-DD)")],
    ) -> DateRange:
        try:
            p = DateRange(start_date, end_date)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if p.days > settings.max_range_days:
            raise InvalidRequest(f"date range is limited to {settings.max_range_days} days")
        return p

    def as_period(p: DateRange) -> Period:
        return Period(start_date=p.start, end_date=p.end)

    # ---------------- routes ----------------
    @app.get("/v1/health", response_model=Health, tags=["operations"])
    def health(deep: Annotated[bool, Query(description="Also check the semantic model")] = False):
        upstream = "unknown"
        if deep:
            backend.check()  # BackendError becomes a 5xx with the standard error body
            upstream = "ok"
        return Health(status="ok", service=SERVICE, version=__version__, backend=backend.name,
                      upstream=upstream, timestamp=_now())

    @app.get("/v1/measures", response_model=list[MeasureInfo], tags=["metrics"])
    def measures():
        return [MeasureInfo(key=m.key, semantic_model_measure=m.dax_name, definition=m.definition)
                for m in CATALOGUE.values()]

    @app.get("/v1/metrics/revenue", response_model=RevenueResponse, tags=["metrics"],
             dependencies=[Depends(only(DATE_FILTERS))])
    def revenue(p: Annotated[DateRange, Depends(period)]):
        s = backend.revenue_summary(p)
        return RevenueResponse(period=as_period(p), currency=CURRENCY, total_revenue=s.total_revenue,
                               total_orders=s.total_orders, average_order_value=s.average_order_value,
                               source=backend.name, generated_at=_now())

    @app.get("/v1/metrics/sales-by-category", response_model=CategoryResponse, tags=["metrics"],
             dependencies=[Depends(only(DATE_FILTERS))])
    def sales_by_category(p: Annotated[DateRange, Depends(period)]):
        rows = backend.sales_by_category(p)
        return CategoryResponse(period=as_period(p), currency=CURRENCY, measure=TOTAL_REVENUE.key,
                                categories=[CategoryRow(category=r.category, revenue=r.revenue) for r in rows],
                                source=backend.name, generated_at=_now())

    @app.get("/v1/metrics/top-products", response_model=TopProductsResponse, tags=["metrics"],
             dependencies=[Depends(only(TOP_PRODUCTS_FILTERS))])
    def top_products(
        p: Annotated[DateRange, Depends(period)],
        limit: Annotated[int, Query(ge=1, le=settings.max_top_products)] = 5,
    ):
        rows = backend.top_products(p, limit)
        return TopProductsResponse(
            period=as_period(p), currency=CURRENCY, measure=TOTAL_REVENUE.key, limit=limit,
            products=[ProductRow(rank=i, product_id=r.product_id, product_name=r.product_name,
                                 category=r.category, revenue=r.revenue) for i, r in enumerate(rows, start=1)],
            source=backend.name, generated_at=_now())

    return app
