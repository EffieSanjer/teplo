from src.cli import FRIENDS
from test_gifts import create
from test_media import photo


def test_reservation_is_secret_and_only_reserver_can_cancel(client, login_as, friend_id):
    owner = login_as(friend_id)
    other = login_as(FRIENDS[1][0])
    item = create(owner, recipient_id=friend_id).json()
    path = f'/api/v1/items/{item["id"]}'
    before = owner.get(path).json()
    result = client.post(path + '/reservation', json={'reserved': True})
    assert result.status_code == 200
    assert result.json()['reservation']['reserved_by_me'] is True
    assert client.post(path + '/reservation', json={'reserved': True}).status_code == 200
    assert owner.get(path).json() == before
    listed = owner.get(f'/api/v1/users/{friend_id}/items/wishlist').json()
    assert next(row for row in listed if row['id'] == item['id']) == before
    assert owner.post(path + '/reservation', json={'reserved': True}).status_code == 404
    data = other.get(path).json()
    assert data['reservation']['reserved_by_me'] is False
    assert data['can_reserve'] is False
    for reserved in (True, False):
        assert other.post(path + '/reservation', json={'reserved': reserved}).status_code == 409
    assert client.post(path + '/reservation', json={'reserved': False}).status_code == 200
    assert other.post(path + '/reservation', json={'reserved': True}).status_code == 200
    # Owner can still delete a reserved wish, without learning about its reservation.
    assert owner.delete(path).status_code == 204


def test_archived_wishes_cannot_be_reserved_but_surprises_can(client, login_as, friend_id):
    owner = login_as(friend_id)
    item = create(owner, recipient_id=friend_id).json()
    path = f'/api/v1/items/{item["id"]}'
    owner.post(path + '/archive', json={'archived': True})
    assert client.post(path + '/reservation', json={'reserved': True}).status_code == 409
    surprise = create(client, recipient_id=friend_id, list_type='surprise').json()
    path = f'/api/v1/items/{surprise["id"]}'
    assert client.post(path + '/reservation', json={'reserved': True}).status_code == 200
    other = login_as(FRIENDS[1][0])
    assert other.get(path).json()['reservation']['reserved_by_me'] is False
    assert other.post(path + '/reservation', json={'reserved': True}).status_code == 409
    assert owner.get(path).status_code == 404
    assert owner.post(path + '/reservation', json={'reserved': True}).status_code == 404
    assert client.post(path + '/reservation', json={'reserved': False}).json()['reservation'] is None


def test_most_wanted_is_owned_by_recipient_and_visible_to_friends(client, login_as, friend_id):
    owner = login_as(friend_id)
    item = create(owner, recipient_id=friend_id).json()
    path = f'/api/v1/items/{item["id"]}'
    assert item['most_wanted'] is False
    assert owner.post(path + '/priority', json={'most_wanted': True}).json()['most_wanted'] is True
    assert client.get(path).json()['most_wanted'] is True
    assert client.post(path + '/priority', json={'most_wanted': False}).status_code == 404
    assert owner.post(path + '/priority', json={'most_wanted': False}).json()['most_wanted'] is False
    surprise = create(client, recipient_id=friend_id, list_type='surprise').json()
    assert client.post(f'/api/v1/items/{surprise["id"]}/priority', json={'most_wanted': True}).status_code == 404
    assert client.post(path + '/surprise').status_code == 404


def test_private_surprise_hidden_in_lists_details_and_media(client, login_as, friend_id):
    other = login_as(FRIENDS[1][0])
    owner = login_as(friend_id)
    mid = client.post('/api/v1/media', files={'file': ('photo.png', photo(), 'image/png')}).json()['id']
    item = create(client, recipient_id=friend_id, list_type='surprise',
                  surprise_visibility='private', image_id=mid).json()
    path = f'/api/v1/items/{item["id"]}'
    for blocked in (other, owner):
        assert blocked.get(path).status_code == 404
        assert blocked.get(f'/api/v1/media/{mid}').status_code == 404
    assert item['id'] not in [i['id'] for i in other.get(f'/api/v1/users/{friend_id}/items/surprise').json()]
    assert client.get(path).status_code == 200
    assert client.get(f'/api/v1/media/{mid}').status_code == 200
    body = {'item_type': 'idea', 'title': 'Сюрприз', 'image_id': mid, 'surprise_visibility': 'friends'}
    assert client.put(path, json=body).status_code == 200
    assert other.get(path).status_code == 200
    assert owner.get(path).status_code == 404
    body['surprise_visibility'] = 'private'
    assert client.put(path, json=body).status_code == 200
    assert other.get(f'/api/v1/media/{mid}').status_code == 404
    client.post(path + '/archive', json={'archived': True})
    assert other.get(path).status_code == 404


def test_certificate_note_limit(client):
    for length, status in ((100, 201), (101, 422)):
        assert create(client, item_type='certificate', url='https://example.com',
                      description='я' * length).status_code == status
    assert create(client, surprise_visibility='unknown').status_code == 422
    assert create(client).json()['surprise_visibility'] == 'friends'


def test_wish_note_limit(client):
    assert create(client, description='я' * 500).status_code == 201
    assert create(client, description='я' * 501).status_code == 422
