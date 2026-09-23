import httpx

from app.ai.tools.map.osm_public_provider import OSMPublicMapProvider


class _FakeResponse:
    def __init__(self, *, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.request = httpx.Request("POST", "https://example.test/api/interpreter")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Server error '{self.status_code}'",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, **kwargs):
        response = self._responses[url]
        if isinstance(response, list):
            next_response = response.pop(0)
        else:
            next_response = response
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


class TestOSMPublicMapProvider:
    def test_search_nearby_recycling_points_retries_same_endpoint_before_failing_over(
        self, app, monkeypatch
    ):
        app.config["OSM_OVERPASS_URL"] = "https://primary.example/api/interpreter"
        app.config["OSM_OVERPASS_FALLBACK_URLS"] = ["https://backup.example/api/interpreter"]
        app.config["OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT"] = 2
        app.config["OSM_OVERPASS_RETRY_BACKOFF_MS"] = 0

        responses = {
            "https://primary.example/api/interpreter": [
                httpx.ConnectTimeout("The handshake operation timed out"),
                _FakeResponse(
                    payload={
                        "elements": [
                            {
                                "type": "node",
                                "id": 1,
                                "lat": 1.3521,
                                "lon": 103.8198,
                                "tags": {
                                    "name": "Recovered Primary Recycling Point",
                                    "amenity": "recycling",
                                },
                            }
                        ]
                    }
                ),
            ],
            "https://backup.example/api/interpreter": _FakeResponse(payload={"elements": []}),
        }

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeClient(responses))

        with app.app_context():
            provider = OSMPublicMapProvider()
            results = provider.search_nearby_recycling_points(
                lat=1.3521, lng=103.8198, area_label="Singapore"
            )

        assert len(results) == 1
        assert results[0]["name"] == "Recovered Primary Recycling Point"
        assert responses["https://primary.example/api/interpreter"] == []

    def test_search_nearby_recycling_points_falls_back_when_primary_overpass_fails(
        self, app, monkeypatch
    ):
        app.config["OSM_OVERPASS_URL"] = "https://primary.example/api/interpreter"
        app.config["OSM_OVERPASS_FALLBACK_URLS"] = ["https://backup.example/api/interpreter"]
        app.config["OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT"] = 2
        app.config["OSM_OVERPASS_RETRY_BACKOFF_MS"] = 0

        responses = {
            "https://primary.example/api/interpreter": [
                _FakeResponse(status_code=500),
                _FakeResponse(status_code=500),
            ],
            "https://backup.example/api/interpreter": _FakeResponse(
                payload={
                    "elements": [
                        {
                            "type": "node",
                            "id": 1,
                            "lat": 1.3521,
                            "lon": 103.8198,
                            "tags": {
                                "name": "Backup Recycling Point",
                                "amenity": "recycling",
                            },
                        }
                    ]
                }
            ),
        }

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeClient(responses))

        with app.app_context():
            provider = OSMPublicMapProvider()
            results = provider.search_nearby_recycling_points(
                lat=1.3521, lng=103.8198, area_label="Singapore"
            )

        assert len(results) == 1
        assert results[0]["name"] == "Backup Recycling Point"
