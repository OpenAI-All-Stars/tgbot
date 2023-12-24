import asyncio
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
                    'text': f'/start {settings.SECRET_INVITE}'
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

    for _ in range(10):
        await asyncio.sleep(1)
        if update_mock.requests_count:
            break
    for _ in range(10):
        await asyncio.sleep(1)
        if send_mock.requests_count:
            break

    assert update_mock.requests_count
    assert send_mock.requests_count
