from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.item import Author, Item, ItemAuthor
from app.schemas.item import (
    AttachmentOut,
    IdentifierImportRequest,
    ImportResult,
    ItemBrief,
    ItemCreate,
    ItemDetail,
    ItemListResponse,
    ItemUpdate,
)

router = APIRouter(prefix="/items", tags=["items"])

_AUTHOR_LOAD = selectinload(Item.authors).selectinload(ItemAuthor.author)


def _author_full_name(given: Optional[str], family: str) -> str:
    return f"{family}, {given}" if given else family


def _load_item(db: Session, item_id: int, owner_id: int) -> Optional[Item]:
    return db.execute(
        select(Item)
        .options(_AUTHOR_LOAD)
        .where(Item.id == item_id, Item.owner_id == owner_id)
    ).scalar_one_or_none()


def _item_to_detail(item: Item) -> ItemDetail:
    return ItemDetail(
        id=item.id,
        type=item.type,
        title=item.title,
        container_title=item.container_title,
        volume=item.volume,
        issue=item.issue,
        pages=item.pages,
        year=item.year,
        doi=item.doi,
        url=item.url,
        abstract=item.abstract,
        language=item.language,
        created_at=item.created_at,
        updated_at=item.updated_at,
        authors=[
            {
                "given_name": ia.author.given_name,
                "family_name": ia.author.family_name,
                "order": ia.order,
            }
            for ia in sorted(item.authors, key=lambda x: x.order)
        ],
    )


def _item_to_brief(item: Item) -> ItemBrief:
    return ItemBrief(
        id=item.id,
        type=item.type,
        title=item.title,
        year=item.year,
        doi=item.doi,
        authors=[
            _author_full_name(ia.author.given_name, ia.author.family_name)
            for ia in sorted(item.authors, key=lambda x: x.order)
        ],
    )


def _save_authors(db: Session, item_id: int, authors: List) -> None:
    for idx, au in enumerate(authors, start=1):
        author = Author(given_name=au.given_name, family_name=au.family_name)
        db.add(author)
        db.flush()
        db.add(ItemAuthor(item_id=item_id, author_id=author.id, order=idx))


@router.get("", response_model=ItemListResponse)
def list_items(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    tag_id: Optional[int] = Query(None),
    collection_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
) -> ItemListResponse:
    query = select(Item).where(Item.owner_id == current_user.id)

    if type:
        query = query.where(Item.type == type)
    if year is not None:
        query = query.where(Item.year == year)
    if q:
        query = query.where(or_(Item.title.contains(q), Item.abstract.contains(q)))

    # TODO: tag_id / collection_id 需 join 关联表，待第四周补充

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()

    if sort:
        field = sort.lstrip("-")
        col = getattr(Item, field, None)
        if col is not None:
            query = query.order_by(col.desc() if sort.startswith("-") else col.asc())
    else:
        query = query.order_by(Item.created_at.desc())

    query = (
        query.options(_AUTHOR_LOAD)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(query).scalars().all()

    return ItemListResponse(
        items=[_item_to_brief(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ItemDetail, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ItemDetail:
    item = Item(
        owner_id=current_user.id,
        type=payload.type.value,
        title=payload.title,
        container_title=payload.container_title,
        volume=payload.volume,
        issue=payload.issue,
        pages=payload.pages,
        year=payload.year,
        doi=payload.doi,
        url=payload.url,
        abstract=payload.abstract,
        language=payload.language,
    )
    db.add(item)
    db.flush()
    _save_authors(db, item.id, payload.authors)
    db.commit()

    item = _load_item(db, item.id, current_user.id)
    return _item_to_detail(item)


@router.get("/{item_id}", response_model=ItemDetail)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ItemDetail:
    item = _load_item(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "条目不存在")
    return _item_to_detail(item)


@router.put("/{item_id}", response_model=ItemDetail)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ItemDetail:
    item = _load_item(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "条目不存在")

    data = payload.model_dump(exclude_unset=True)
    authors = data.pop("authors", None)
    for key, value in data.items():
        if key == "type" and value is not None:
            value = value.value
        setattr(item, key, value)

    if authors is not None:
        db.execute(delete(ItemAuthor).where(ItemAuthor.item_id == item.id))
        _save_authors(db, item.id, authors)

    db.commit()
    item = _load_item(db, item_id, current_user.id)
    return _item_to_detail(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    item = _load_item(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "条目不存在")
    db.delete(item)
    db.commit()


@router.post(
    "/import/identifier",
    response_model=ItemDetail,
    status_code=status.HTTP_201_CREATED,
)
def import_by_identifier(
    payload: IdentifierImportRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ItemDetail:
    # TODO: 待 services/metadata 实现后接入 CrossRef / arXiv / PubMed 抓取
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "标识符导入待第三周实现（REQ-IM-02~05）",
    )


@router.post(
    "/import/file",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
)
def import_by_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ImportResult:
    # TODO: 待 services/importer 实现后接入 BibTeX / RIS 解析
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "文件批量导入待第三周实现（REQ-IM-06~08）",
    )


@router.post(
    "/{item_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AttachmentOut:
    item = _load_item(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "条目不存在")
    # TODO: 待附件存储逻辑实现后保存文件并记录元数据（REQ-IM-09）
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "附件上传待第三周实现",
    )