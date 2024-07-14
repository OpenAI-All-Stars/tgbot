from datetime import datetime

import pytest


@pytest.mark.parametrize(
    'start_text, response_expected, users_expected',
    [
        ('/start eyJ0IjoxNzAzNDc3MTAwLjY4OTIzMDd9.BbWPzLxEwhu6ZWUIqpq_WLeR6cwzwp9bUfa07Ja8W_A', 'Добро пожаловать!', [{
            'user_id': 111,
            'full_name': 'cat',
            'username': '',
            'invite_code': '',
        }]),
    ],
)
async def test_success(settings, mock_server, db, start_text, response_expected, users_expected):
    update_mock = mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/getUpdates',
        request_text='timeout=10&allowed_updates=%5B%22message%22%2C+%22pre_checkout_query%22%5D',
        response_json={
            'ok': True,
            'result': [{
                'update_id': 1,
                'message': {
                    'message_id': 11,
                    'date': datetime.now().isoformat(),
                    'chat': {
                        'id': 111,
                        'type': 'private',
                    },
                    'from_user': {
                        'id': 111,
                        'is_bot': False,
                        'first_name': 'cat',
                    },
                    'text': start_text
                },
            }],
        },
    )
    mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/getUpdates',
        request_text='offset=2&timeout=10&allowed_updates=%5B%22message%22%2C+%22pre_checkout_query%22%5D',
        response_json={
            'ok': True,
            'result': [],
        },
    )
    send_mock = mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/sendMessage',
        response_json={
            'ok': True,
            'result': {
                'message_id': 22,
                'date': datetime.now().isoformat(),
                'chat': {
                    'id': 111,
                    'type': 'private',
                },
            },
        },
    )
    mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/sendChatAction',
        response_json={
            'ok': True,
        },
    )

    assert await update_mock.wait()
    assert await send_mock.wait()

    assert [r.encode_text() for r in send_mock.requests] == [{
        'chat_id': '111',
        'text': response_expected,
        'parse_mode': 'Markdown',
    }]
    got = await db.fetch('SELECT * FROM users')
    assert [dict(x) for x in got] == users_expected
