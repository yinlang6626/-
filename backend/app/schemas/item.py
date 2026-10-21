import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DOI_PATTERN = r"^10\.\d{4,}/\S+$"
MIN_YEAR = 1500
MAX_YEAR = datetime.now().year + 1


class ItemType(str, Enum):
    JOURNAL_ARTICLE = "journal-article"
    CONFERENCE_PAPER = "conference-paper"
    THESIS = "thesis"
    BOOK = "book"
    WEBPAGE = "webpage"


class IdentifierType(str, Enum):
    DOI = "doi"
    ARXIV = "arxiv"
    PMID = "pmid"


class AuthorCreate(BaseModel):
    given_name: Optional[str] = Field(None, max_length=64)
    family_name: str = Field(..., min_length=1, max_length=64)

    model_config = ConfigDict(from_attributes=True)


class AuthorOut(BaseModel):
    given_name: Optional[str] = None
    family_name: str
    order: int

    model_config = ConfigDict(from_attributes=True)


class ItemBase(BaseModel):
    type: ItemType
    title: str = Field(..., min_length=1, max_length=512)
    container_title: Optional[str] = Field(None, max_length=512)
    volume: Optional[str] = Field(None, max_length=32)
    issue: Optional[str] = Field(None, max_length=32)
    pages: Optional[str] = Field(None, max_length=32)
    year: Optional[int] = Field(None, ge=MIN_YEAR, le=MAX_YEAR)
    doi: Optional[str] = Field(None, max_length=128)
    url: Optional[str] = Field(None, max_length=512)
    abstract: Optional[str] = None
    language: Optional[str] = Field("zh", max_length=8)

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(DOI_PATTERN, v):
            raise ValueError("DOI 格式非法，应为 10.xxxx/xxx 形式")
        return v


class ItemCreate(ItemBase):
    authors: List[AuthorCreate] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    type: Optional[ItemType] = None
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    container_title: Optional[str] = Field(None, max_length=512)
    volume: Optional[str] = Field(None, max_length=32)
    issue: Optional[str] = Field(None, max_length=32)
    pages: Optional[str] = Field(None, max_length=32)
    year: Optional[int] = Field(None, ge=MIN_YEAR, le=MAX_YEAR)
    doi: Optional[str] = Field(None, max_length=128)
    url: Optional[str] = Field(None, max_length=512)
    abstract: Optional[str] = None
    language: Optional[str] = Field(None, max_length=8)
    authors: Optional[List[AuthorCreate]] = None

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(DOI_PATTERN, v):
            raise ValueError("DOI 格式非法，应为 10.xxxx/xxx 形式")
        return v


class ItemBrief(BaseModel):
    id: int
    type: ItemType
    title: str
    year: Optional[int] = None
    doi: Optional[str] = None
    authors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ItemDetail(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    authors: List[AuthorOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: List[ItemBrief]
    total: int
    page: int = 1
    page_size: int = 20


class IdentifierImportRequest(BaseModel):
    identifier_type: IdentifierType
    value: str = Field(..., min_length=1)


class ImportSkipped(BaseModel):
    raw: str
    reason: str


class ImportResult(BaseModel):
    imported: List[ItemBrief] = Field(default_factory=list)
    skipped: List[ImportSkipped] = Field(default_factory=list)


class AttachmentOut(BaseModel):
    id: int
    filename: str
    size: int
    mime_type: str

    model_config = ConfigDict(from_attributes=True)