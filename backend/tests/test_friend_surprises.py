from fastapi.testclient import TestClient
from sqlalchemy import select

from src.infrastructure.database import CommunityIntegration, FriendSurpriseSpace, Item
from src.main import app
from test_friendships import invite, people  # noqa: F401
from test_media import photo
from test_private_telegram import login, private_settings as private_login_settings  # noqa: F401
from src.config import get_settings


def test_surprises_shared_by_direct_friends_hidden_from_recipient_and_outsiders(db, people):  # noqa: F811
    a, b, c, aa, bb, cc = people
    uid = aa['user']['id']
    assert b.post('/api/v1/friends/accept', json={'token': invite(a)}).status_code == 200
    mid = b.post('/api/v1/media', files={'file': ('photo.png', photo(), 'image/png')}).json()['id']
    result = b.post('/api/v1/items', json={
        'recipient_id': uid, 'list_type': 'surprise', 'item_type': 'idea', 'title': 'Секрет', 'image_id': mid,
    })
    assert result.status_code == 201, result.text
    item = result.json()
    space = db.get(FriendSurpriseSpace, uid)
    assert space.community_id not in {aa['community_id'], bb['community_id'], cc['community_id']}
    assert db.get(CommunityIntegration, space.community_id) is None
    assert db.get(Item, item['id']).community_id == space.community_id
    assert b.get(f'/api/v1/items/{item["id"]}').status_code == 200
    for blocked in (a, c):
        assert blocked.get(f'/api/v1/items/{item["id"]}').status_code == 404
        assert blocked.get(f'/api/v1/media/{mid}').status_code == 404
        assert blocked.get(f'/api/v1/users/{uid}/items/surprise').status_code == 404
    # Being friends with the author is insufficient.
    assert c.post('/api/v1/friends/accept', json={'token': invite(b)}).status_code == 200
    assert c.get(f'/api/v1/items/{item["id"]}').status_code == 404
    # A new direct friend of the recipient sees the shared list, but cannot manage others' records.
    assert c.post('/api/v1/friends/accept', json={'token': invite(a)}).status_code == 200
    listed = c.get(f'/api/v1/users/{uid}/items/surprise').json()
    assert [i['id'] for i in listed] == [item['id']]
    assert listed[0]['can_manage'] is False
    assert c.get(f'/api/v1/media/{mid}').status_code == 200
    assert c.put(f'/api/v1/items/{item["id"]}', json={'item_type': 'idea', 'title': 'Подмена'}).status_code == 404
    assert c.delete(f'/api/v1/items/{item["id"]}').status_code == 404
    assert c.post(f'/api/v1/items/{item["id"]}/archive', json={'archived': True}).status_code == 404
    assert b.put(f'/api/v1/items/{item["id"]}', json={'item_type': 'idea', 'title': 'Обновлено', 'image_id': mid}).status_code == 200
    assert b.post(f'/api/v1/items/{item["id"]}/archive', json={'archived': True}).status_code == 200
    assert c.get(f'/api/v1/users/{uid}/items/surprise').json()[0]['archived_at'] is not None
    assert a.get(f'/api/v1/media/{mid}').status_code == 404
    # Removing a friendship revokes even the author's access, without destroying others' list.
    assert a.delete(f'/api/v1/friends/{bb["user"]["id"]}').status_code == 204
    assert b.get(f'/api/v1/items/{item["id"]}').status_code == 404
    assert b.get(f'/api/v1/media/{mid}').status_code == 404
    assert b.delete(f'/api/v1/items/{item["id"]}').status_code == 404
    assert c.get(f'/api/v1/items/{item["id"]}').status_code == 200
    assert a.delete(f'/api/v1/friends/{cc["user"]["id"]}').status_code == 204
    assert c.get(f'/api/v1/media/{mid}').status_code == 404
    assert a.get(f'/api/v1/items/{item["id"]}').status_code == 404


def test_copy_wish_and_certificate_into_same_friend_list_and_reentry(db, people):  # noqa: F811
    a, b, c, aa, _, _ = people
    uid = aa['user']['id']
    assert b.post('/api/v1/friends/accept', json={'token': invite(a)}).status_code == 200
    assert c.post('/api/v1/friends/accept', json={'token': invite(a)}).status_code == 200
    mid = a.post('/api/v1/media', files={'file': ('photo.png', photo(), 'image/png')}).json()['id']
    wish = a.post('/api/v1/items', json={
        'recipient_id': uid, 'list_type': 'wishlist', 'item_type': 'idea', 'title': 'Желание', 'image_id': mid,
    }).json()
    copied = b.post(f'/api/v1/items/{wish["id"]}/surprise')
    assert copied.status_code == 201
    cert = c.post('/api/v1/items', json={
        'recipient_id': uid, 'list_type': 'surprise', 'item_type': 'certificate', 'url': 'https://example.com',
    })
    assert cert.status_code == 201
    assert len(db.scalars(select(FriendSurpriseSpace)).all()) == 1
    assert len(b.get(f'/api/v1/users/{uid}/items/surprise').json()) == 2
    assert len(c.get(f'/api/v1/users/{uid}/items/surprise').json()) == 2
    assert a.get(f'/api/v1/items/{copied.json()["id"]}').status_code == 404
    # Shared source image remains readable via the recipient's own wish, not the secret copy.
    assert a.get(f'/api/v1/media/{mid}').status_code == 200
    assert a.get(f'/api/v1/items/{wish["id"]}').json()['list_type'] == 'wishlist'
    assert a.post('/api/v1/items', json={
        'recipient_id': uid, 'list_type': 'surprise', 'item_type': 'idea', 'title': 'Себе',
    }).status_code == 404
    login(b, get_settings(), 456)
    assert b.get(f'/api/v1/items/{copied.json()["id"]}').status_code == 200
    assert b.delete(f'/api/v1/items/{copied.json()["id"]}').status_code == 204
    assert a.get(f'/api/v1/items/{wish["id"]}').status_code == 200


def test_friend_surprise_space_cannot_be_used_as_a_login_community(db, people, login_as):  # noqa: F811
    a, b, _, aa, bb, _ = people
    uid = aa['user']['id']
    b.post('/api/v1/friends/accept', json={'token': invite(a)})
    b.post('/api/v1/items', json={'recipient_id': uid, 'list_type': 'surprise', 'item_type': 'idea', 'title': 'Секрет'})
    space = db.get(FriendSurpriseSpace, uid)
    assert login_as(bb['user']['id'], space.community_id).get('/api/v1/auth/session').status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get(f'/api/v1/users/{uid}/items/surprise').status_code == 401
