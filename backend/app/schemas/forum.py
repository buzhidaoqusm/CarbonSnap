from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PostOut(BaseModel):
    id: int
    author_id: int
    author_username: str | None
    author_avatar_url: str | None
    title: str
    content: str
    # A JSON array of image URLs, stored and returned as a string.
    image_urls_json: str | None
    status: str
    # None where a response does not count them (the update response), and
    # liked_by_user is None for anonymous readers.
    like_count: int | None
    comment_count: int | None
    liked_by_user: bool | None
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    created_at: str


class PostPage(BaseModel):
    items: list[PostOut]
    total: int
    page: int
    per_page: int


class CommentOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    author_username: str | None
    author_avatar_url: str | None
    parent_comment_id: int | None
    content: str
    status: str
    like_count: int | None
    liked_by_user: bool | None
    created_at: str


class CommentList(BaseModel):
    items: list[CommentOut]
    total: int


class LikeResult(BaseModel):
    liked: bool
    like_count: int


class LongViewResult(BaseModel):
    tracked: bool
    reason: str | None = None


class UploadResult(BaseModel):
    url: str


# Request bodies. Fields default to "" or None and are checked in the routes,
# so a missing or mistyped field gets the message users have seen before.


class PostIn(BaseModel):
    title: str = ""
    content: str = ""
    image_urls_json: str | None = None


class PostUpdateIn(BaseModel):
    # Blank or absent leaves the field as it is.
    title: str | None = None
    content: str | None = None
    image_urls_json: str | None = None


class CommentIn(BaseModel):
    content: str = ""
    parent_comment_id: Any = None


class LikeIn(BaseModel):
    target_type: str = ""
    target_id: Any = None


class UploadIn(BaseModel):
    image: Any = None
