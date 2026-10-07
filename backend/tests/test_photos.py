"""Spec 4 R1b: profile pictures."""

import pytest

from tests import helpers


def test_upload_resizes_to_a_square_and_returns_a_link(client):
    parent = helpers.register_parent(client, photo=False)
    response = helpers.upload_photo(client, parent["headers"], helpers.image_bytes((1200, 800), "JPEG"))
    assert response.status_code == 200
    url = response.json()["user"]["photo_url"]
    picture = client.get(url.replace("http://localhost:8000", ""))
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/jpeg"

    from io import BytesIO

    from PIL import Image
    assert Image.open(BytesIO(picture.content)).size == (512, 512)


@pytest.mark.parametrize("data,filename", [(b"not an image", "me.png"), (helpers.image_bytes(fmt="GIF"), "me.gif")])
def test_only_jpg_png_or_webp(client, data, filename):
    parent = helpers.register_parent(client, photo=False)
    assert helpers.upload_photo(client, parent["headers"], data, filename).status_code == 422


def test_more_than_5_mb_is_rejected(client):
    parent = helpers.register_parent(client, photo=False)
    assert helpers.upload_photo(client, parent["headers"], b"0" * (5 * 1024 * 1024 + 1)).status_code == 413


def test_photo_link_is_signed(client):
    parent = helpers.register_parent(client)
    url = client.get("/v1/auth/me", headers=parent["headers"]).json()["user"]["photo_url"]
    tampered = url.replace("sig=", "sig=0")
    assert client.get(tampered.replace("http://localhost:8000", "")).status_code == 403


def test_tutor_photo_is_public_on_the_listing(client, admin_headers):
    tutor = helpers.approved_tutor(client, admin_headers)
    helpers.upload_photo(client, tutor["headers"])
    assert client.get(f"/v1/tutors/{tutor['id']}").json()["photo_url"]


def test_admin_removes_an_inappropriate_photo_and_user_is_asked_for_a_new_one(client, admin_headers):
    parent = helpers.register_parent(client)
    response = client.delete(f"/v1/admin/users/{parent['id']}/photo", headers=admin_headers)
    assert response.status_code == 204
    me = client.get("/v1/auth/me", headers=parent["headers"]).json()
    assert me["user"]["photo_url"] is None
    titles = [n["title"] for n in client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"]]
    assert "Please upload a new profile picture" in titles
    assert client.delete(f"/v1/admin/users/{parent['id']}/photo", headers=parent["headers"]).status_code == 403
