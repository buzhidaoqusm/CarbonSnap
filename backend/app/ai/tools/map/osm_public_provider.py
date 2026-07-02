from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from time import sleep
from typing import Any

import httpx
from flask import current_app


class MapProviderError(RuntimeError):
    pass


class OSMPublicMapProvider:
    def __init__(self) -> None:
        self.nominatim_url = current_app.config["OSM_NOMINATIM_URL"].rstrip("/")
        self.overpass_url = current_app.config["OSM_OVERPASS_URL"]
        self.overpass_fallback_urls = list(current_app.config.get("OSM_OVERPASS_FALLBACK_URLS", []))
        self.overpass_timeout_seconds = float(current_app.config.get("OSM_OVERPASS_TIMEOUT_SECONDS", 30.0))
        self.overpass_connect_timeout_seconds = float(
            current_app.config.get("OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS", 8.0)
        )
        self.overpass_max_attempts_per_endpoint = max(
            1, int(current_app.config.get("OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT", 2))
        )
        self.overpass_retry_backoff_ms = max(
            0, int(current_app.config.get("OSM_OVERPASS_RETRY_BACKOFF_MS", 400))
        )
        self.user_agent = current_app.config["OSM_USER_AGENT"]
        self.search_radius_meters = current_app.config["AI_MAP_SEARCH_RADIUS_METERS"]
        self.search_limit = current_app.config["AI_MAP_SEARCH_LIMIT"]
        self.recycling_tags = current_app.config["AI_OSM_RECYCLING_TAGS"]

    def geocode_area(self, area: str) -> dict[str, Any]:
        query = area.strip()
        if not query:
            raise MapProviderError("Area input cannot be empty.")

        with httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=True,
        ) as client:
            response = client.get(
                f"{self.nominatim_url}/search",
                params={
                    "format": "jsonv2",
                    "q": query,
                    "limit": 1,
                    "addressdetails": 1,
                },
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            raise MapProviderError("No area match found for the provided manual location.")

        first = results[0]
        return {
            "lat": float(first["lat"]),
            "lng": float(first["lon"]),
            "normalized_area": first.get("display_name", query),
        }

    def search_nearby_recycling_points(
        self,
        *,
        lat: float,
        lng: float,
        area_label: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self._build_overpass_query(lat=lat, lng=lng)
        payload = self._fetch_overpass_payload(query)

        elements = payload.get("elements", [])
        normalized_results = [
            self._normalize_osm_element(element, lat=lat, lng=lng, area_label=area_label)
            for element in elements
        ]
        filtered_results = [item for item in normalized_results if item is not None]
        filtered_results.sort(key=lambda item: item["distance_meters"])
        return filtered_results[: self.search_limit]

    def _fetch_overpass_payload(self, query: str) -> dict[str, Any]:
        errors: list[str] = []
        for url in self._candidate_overpass_urls():
            for attempt in range(1, self.overpass_max_attempts_per_endpoint + 1):
                try:
                    with httpx.Client(
                        headers={"User-Agent": self.user_agent},
                        timeout=httpx.Timeout(
                            self.overpass_timeout_seconds,
                            connect=self.overpass_connect_timeout_seconds,
                        ),
                        follow_redirects=True,
                    ) as client:
                        response = client.post(
                            url,
                            content=query,
                            headers={"Content-Type": "text/plain"},
                        )
                        response.raise_for_status()
                        return response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    errors.append(f"{url} (attempt {attempt}/{self.overpass_max_attempts_per_endpoint}): {exc}")
                    if attempt < self.overpass_max_attempts_per_endpoint:
                        self._sleep_before_retry(attempt)

        last_error = errors[-1] if errors else "No Overpass endpoint is configured."
        raise MapProviderError(f"Nearby map providers are temporarily unavailable. {last_error}")

    def _candidate_overpass_urls(self) -> list[str]:
        urls = [self.overpass_url, *self.overpass_fallback_urls]
        deduped: list[str] = []
        for url in urls:
            normalized = str(url or "").strip()
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped

    def _build_overpass_query(self, *, lat: float, lng: float) -> str:
        segments = []
        for tag in self.recycling_tags:
            key = tag["key"]
            value = tag["value"]
            segments.extend(
                [
                    f'node(around:{self.search_radius_meters},{lat},{lng})["{key}"="{value}"];',
                    f'way(around:{self.search_radius_meters},{lat},{lng})["{key}"="{value}"];',
                    f'relation(around:{self.search_radius_meters},{lat},{lng})["{key}"="{value}"];',
                ]
            )

        query_body = "\n".join(segments)
        query_timeout_seconds = max(5, int(round(self.overpass_timeout_seconds)))
        return f"""
[out:json][timeout:{query_timeout_seconds}];
(
{query_body}
);
out center tags;
"""

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.overpass_retry_backoff_ms <= 0:
            return

        backoff_seconds = (self.overpass_retry_backoff_ms / 1000.0) * attempt
        sleep(backoff_seconds)

    def _normalize_osm_element(
        self,
        element: dict[str, Any],
        *,
        lat: float,
        lng: float,
        area_label: str | None = None,
    ) -> dict[str, Any] | None:
        tags = element.get("tags", {})
        item_lat = element.get("lat") or element.get("center", {}).get("lat")
        item_lng = element.get("lon") or element.get("center", {}).get("lon")
        if item_lat is None or item_lng is None:
            return None

        item_lat = float(item_lat)
        item_lng = float(item_lng)
        distance_meters = _haversine_distance_meters(lat, lng, item_lat, item_lng)
        name = tags.get("name") or tags.get("operator") or "Recycling point"

        address_bits = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
            tags.get("addr:state"),
            tags.get("addr:country"),
        ]
        address = ", ".join([bit for bit in address_bits if bit]) or tags.get("address") or area_label or "Address unavailable"

        category = (
            tags.get("recycling_type")
            or tags.get("amenity")
            or tags.get("waste")
            or "recycling"
        )

        return {
            "name": name,
            "address": address,
            "lat": round(item_lat, 6),
            "lng": round(item_lng, 6),
            "distance_meters": int(distance_meters),
            "source": "openstreetmap",
            "category": str(category).replace("_", " "),
            "osm_url": f"https://www.openstreetmap.org/?mlat={item_lat}&mlon={item_lng}#map=18/{item_lat}/{item_lng}",
        }


def _haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_m = 6_371_000

    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    start_lat = radians(lat1)
    end_lat = radians(lat2)

    a = sin(delta_lat / 2) ** 2 + cos(start_lat) * cos(end_lat) * sin(delta_lng / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c
