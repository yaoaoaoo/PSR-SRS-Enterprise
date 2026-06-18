"""System status API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_index_manager, get_profile_service
from app.core.config import settings
from app.db.session import check_db_connection
from app.schemas.common import DataResponse
from app.schemas.system import IndexStatusResponse, ProfileStatusResponse, SystemStatusResponse
from app.services.index_manager import IndexManager
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status", response_model=DataResponse[SystemStatusResponse])
def system_status(request: Request):
    db_ok = check_db_connection()
    schema_ok = False
    if db_ok:
        from app.db.session import _get_session_factory
        try:
            s = _get_session_factory()()
            s.execute(s.bind.dialect.dialect_description("SELECT 1 FROM items LIMIT 0"))
            schema_ok = True
            s.close()
        except Exception:
            pass

    container = request.app.state.service_container
    idx = container.index_manager.get_status()
    prof = container.profile_service.get_status()

    return DataResponse(data=SystemStatusResponse(
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database_connected=db_ok,
        schema_available=schema_ok,
        index_ready=idx.ready,
        index_generation=idx.generation,
        profile_ready=prof.ready,
        profile_generation=prof.generation,
    ))


@router.get("/index", response_model=DataResponse[IndexStatusResponse])
def index_status(idx: IndexManager = Depends(get_index_manager)):
    st = idx.get_status()
    return DataResponse(data=IndexStatusResponse(
        ready=st.ready,
        generation=st.generation,
        built_at=st.built_at,
        item_count=st.item_count,
        error_message=st.error_message,
    ))


@router.get("/profiles", response_model=DataResponse[ProfileStatusResponse])
def profile_status(prof: ProfileService = Depends(get_profile_service)):
    st = prof.get_status()
    return DataResponse(data=ProfileStatusResponse(
        ready=st.ready,
        generation=st.generation,
        built_at=st.built_at,
        profile_count=st.profile_count,
        error_message=st.error_message,
    ))
