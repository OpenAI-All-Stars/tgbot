from datetime import datetime


async def test_success(settings, mock_server):
    update_mock = mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/getUpdates',
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
                        'id': 2,
                        'is_bot': False,
                        'first_name': 'cat',
                    },
                    'text': f'/start eyJ0IjoxNzAzNDc3MTAwLjY4OTIzMDd9.BbWPzLxEwhu6ZWUIqpq_WLeR6cwzwp9bUfa07Ja8W_A'
                },
            }],
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
                    'id': 222,
                    'type': 'private',
                },
            },
        },
    )

    assert await update_mock.wait()
    assert await send_mock.wait()

    got = send_mock.requests[0].encode_text()
    assert got == {
        'chat_id': '111',
        'text': 'Добро пожаловать!',
        'parse_mode': 'Markdown',
    }
