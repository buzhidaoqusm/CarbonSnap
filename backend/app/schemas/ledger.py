from __future__ import annotations

from pydantic import BaseModel


class WasteRecordOut(BaseModel):
    id: int
    waste_type: str | None
    co2_saved_kg: float
    carbon_points: int
    image_url: str | None
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    created_at: str


class WasteRecordPage(BaseModel):
    items: list[WasteRecordOut]
    total: int
    page: int
    per_page: int


class TransactionOut(BaseModel):
    id: int
    type: str
    points_delta: int
    co2_delta_kg: float
    source_type: str
    source_id: int | None
    created_at: str


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    per_page: int


class LedgerSummary(BaseModel):
    total_carbon_amount: float
    current_points: int
    total_points_earned: int


class Badge(BaseModel):
    id: str
    name: str
    description: str


class Gamification(BaseModel):
    level: int
    level_title: str
    xp_in_level: int
    xp_to_next: int
    total_carbon_amount: float
    current_points: int
    total_points_earned: int
    score: int
    badges: list[Badge]


class LeaderboardEntry(BaseModel):
    user_id: int
    avatar_url: str
    weekly_points_gain: int
    rank: int


class WeeklyLeaderboard(BaseModel):
    window_days: int
    top_users: list[LeaderboardEntry]
    current_user_rank: LeaderboardEntry | None
