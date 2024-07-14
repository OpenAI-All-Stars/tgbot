from datetime import datetime
from unittest.mock import ANY


async def test_success(tg_server, settings, mock_server, db):
    await db.execute('INSERT INTO users (user_id) VALUES (111)')
    await db.execute('INSERT INTO wallets (user_id, microdollars) VALUES (111, 1)')

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
                    'text': 'Привет'
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
    mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/sendChatAction',
        response_json={
            'ok': True,
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
    completions_mock = mock_server.add_request_mock(
        'POST', '/chat/completions',
        response_json={
            'id': 'chatcmpl-abc123',
            'object': 'chat.completion',
            'created': 1677858242,
            'model': 'gpt-3.5-turbo-0613',
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 10,
                'total_tokens': 20
            },
            'choices': [
                {
                    'message': {
                        'role': 'assistant',
                        'content': 'Пока'
                    },
                    'logprobs': None,
                    'finish_reason': 'stop',
                    'index': 0
                }
            ]
        },
    )

    assert await update_mock.wait()
    assert await send_mock.wait()
    assert await completions_mock.wait()

    assert [r.encode_text() for r in send_mock.requests] == [{
        'chat_id': '111',
        'text': 'Пока',
        'parse_mode': 'MarkdownV2',
    }]
    got = await db.fetch('SELECT * FROM wallets_history')
    assert [dict(x) for x in got] == [{'user_id': 111, 'microdollars': -240, 'created_at': ANY}]
    got = await db.fetch('SELECT * FROM wallets')
    assert [dict(x) for x in got] == [{'user_id': 111, 'microdollars': -239}]
