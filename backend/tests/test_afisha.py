import json

import pytest

from src.integrations.product_metadata.afisha import fetch_session, session_api_url
from src.integrations.product_metadata.network import FetchError

URL = ('https://widget.afisha.yandex.ru/w/sessions/'
       'OTc1MzZ8OTEwNTMzfDEyMTAxOTYyfDE3OTY0MDE4MDAwMDA%3D'
       '?clientKey=bb40c7f4-11ee-4f00-9804-18ee56565c87&embed=true&utm_source=test')


def test_widget_url():
    endpoint = session_api_url(URL)
    assert '/api/tickets/v1/sessions/' in endpoint
    assert 'embed' not in endpoint and 'utm_' not in endpoint
    assert session_api_url(endpoint) == endpoint


@pytest.mark.parametrize('url', [
    URL.replace('widget.afisha.yandex.ru', 'widget.afisha.yandex.ru.evil.test'),
    URL.replace('https://', 'https://user:password@'),
    URL.replace('https://', 'http://'),
    URL.replace('clientKey=', 'missing='),
    URL.replace('OTc1MzZ8OTEwNTMzfDEyMTAxOTYyfDE3OTY0MDE4MDAwMDA%3D', 'invalid'),
])
def test_unsafe_or_incomplete_widget_url(url):
    assert session_api_url(url) is None


def test_session_uses_event_photo_not_hallplan_or_seat_prices():
    photo = 'https://avatars.mds.yandex.net/get-tickets/1/event/orig'
    payload = {'status': 'success', 'result': {'session': {
        'event': {'name': 'Concert', 'images': [
            {'url': 'http://127.0.0.1/private'}, {'url': photo},
        ]}, 'prices': [{'value': 100}], 'hallplanImage': {'url': 'https://example.com/hall.jpg'},
    }}}
    result = fetch_session('endpoint', lambda *args: (json.dumps(payload).encode(), 'application/json', ''), 10000)
    assert result == {'title': 'Concert', 'image_urls': [photo], 'image_url': photo}


def test_invalid_session_response():
    with pytest.raises(FetchError):
        fetch_session('endpoint', lambda *args: (b'{}', 'application/json', ''), 10000)
