"""Items API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.repositories.item_repository import ItemRepository
from app.schemas.common import DataResponse, ListResponse, PaginationMeta
from app.schemas.item import ItemSchema

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("", response_model=ListResponse[ItemSchema])
def list_items(
    session: Session = Depends(get_db_session),
):
    repo = ItemRepository(session)
    items = repo.list(limit=100)
    total = repo.count()

    return ListResponse(
        data=[_to_schema(i) for i in items],
        pagination=PaginationMeta(offset=0, limit=100, total=total, returned=len(items)),
    )


@router.get("/{item_id}", response_model=DataResponse[ItemSchema])
def get_item(item_id: str, session: Session = Depends(get_db_session)):
    from fastapi.responses import JSONResponse

    repo = ItemRepository(session)
    item = repo.get_by_id(item_id)
    if item is None:
        from app.schemas.common import ApiMeta, ErrorDetail, ErrorResponse
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(code="not_found", message=f"Item {item_id!r} not found"),
                meta=ApiMeta(),
            ).model_dump(),
        )
    return DataResponse(data=_to_schema(item))


def _to_schema(item) -> ItemSchema:
    return ItemSchema(
        item_id=item.item_id,
        title=item.title,
        description=item.description or "",
        category=item.category,
        subcategory=item.subcategory,
        brand=item.brand,
        price=str(item.price),
        quality_score=item.quality_score,
        popularity_score=item.popularity_score,
        is_cold_start=item.is_cold_start,
        created_at=item.created_at,
    )
