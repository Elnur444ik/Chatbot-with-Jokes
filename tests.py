from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock, ANY

from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent, VkBotEvent

import settings
from Bot import Bot


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class Test1(TestCase):
    RAW_EVENT = {'group_id': 215289898, 'type': 'message_new', 'event_id': '31bc3069e21ae1a5adec6b92f5153050caaa573e',
                 'v': '5.131', 'object':
                     {'message': {'date': 1660376082, 'from_id': 96348546, 'id': 57, 'out': 0, 'attachments': [],
                                  'conversation_message_id': 54, 'fwd_messages': [], 'important': False,
                                  'is_hidden': False,
                                  'peer_id': 96348546, 'random_id': 0, 'text': '32423'},
                      'client_info': {
                          'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link', 'callback',
                                             'intent_subscribe', 'intent_unsubscribe'],
                          'keyboard': True, 'inline_keyboard': True, 'carousel': True, 'lang_id': 0}}}

    def test_run(self):
        count = 5
        obj = {'a': 1}
        events = [obj] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_mock_listen_mock = Mock()
        long_poller_mock_listen_mock.listen = long_poller_mock

        with patch('Bot.vk_api.VkApi'):
            with patch('Bot.VkBotLongPoll', return_value=long_poller_mock_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.send_image = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    INPUTS = [
        'Привет',
        'А когда',
        'Где будет конференция?',
        'Зарегистрируй меня',
        'Вениамин',
        'мой адрес email@email',
        'email@email.ru',
    ]
    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,
        settings.INTENTS[0]['answer'],
        settings.INTENTS[1]['answer'],
        settings.SCENARIOS['registration']['steps']['step1']['text'],
        settings.SCENARIOS['registration']['steps']['step2']['text'],
        settings.SCENARIOS['registration']['steps']['step2']['failure_text'],
        settings.SCENARIOS['registration']['steps']['step3']['text'].format(name='Вениамин', email='email@email.ru')
    ]

    @isolate_db
    def test_run_ok(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_text
            events.append(VkBotEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('Bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.send_image = Mock()
            bot.run()

        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_image_generation(self):
        with open('files\\', 'rb') as avatar_file: # TODO вписать аватар файл
            avatar_mock = Mock()
            avatar_mock.content = avatar_file.read()

        with patch('requests.get', return_value=avatar_mock)
            ticket_file = generate_ticket('Qwe', 'email@email.com')

        with open('files\\ticket-example.png', 'rb') as expected_file: # TODO с чем сравнивается
            expected_bytes = expected_file.read()

        assert ticket_file.read() == expected_bytes