from pydantic import BaseModel


class SearchResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int
