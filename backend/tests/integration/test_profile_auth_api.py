class TestProfileAuthApi:
    def test_authenticated_user_can_update_bio(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch(
            "/api/auth/me", json={"bio": "Building a lower-waste routine."}, headers=headers
        )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["user"]["bio"] == "Building a lower-waste routine."

        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.get_json()["data"]["user"]["bio"] == "Building a lower-waste routine."

    def test_bio_has_length_limit(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch("/api/auth/me", json={"bio": "x" * 501}, headers=headers)

        assert response.status_code == 400
        assert response.get_json()["message"] == "Bio must be 500 characters or fewer."
