from random import randint
import logging

import requests
from bs4 import BeautifulSoup

import handlers
from models import get_joke, get_photo

try:
    import settings
except ImportError:
    exit('Do cp settings.py.default settings.py and set token!')

import vk_api  # v.11.9.9
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

log = logging.getLogger('bot')


def configure_logging():
    """
    Настройка логирования
    """
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler(filename='bot.log', encoding='utf8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class Bot:
    """
    Чат-бот выдающий анекдоты
    Use Python310

    Бот может выдавать случайный анекдот, 30 лучших анекдотов (самые залайканные) и
    анекдоты от Эльнура (мои любимые анекдоты):
    Принцип работы:
    а) спрашиваем какой анекдот пользователь хочет услышать:
    - если случайный, то берем с сайта https://baneks.ru/ случайный анекдот (парсим его);
    - если из лучших, то просим число от 1 до 30 (всего 30 лучших анекдтов) и выдаем;
    - если от Эльнура, то берем из БД заранее внесенный анекдот. Выбирается случайным образом;
    б) помимо анекдота прикрепляем картинку (смеющиеся люди из кривого зеркала).
    Ссылки на картинки заранее внесены в БД. Сами картинки находятся в папке files.
    """

    def __init__(self, group_id, token):
        """
        :param group_id: group id из группы VK
        :param token: секретный токен (уникальный)
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=token)
        self.long_poller = VkBotLongPoll(vk=self.vk, group_id=self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """Запуск бота"""

        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('Ошибка в обработке события')

    #    @db_session
    def on_event(self, event):
        """
        "Слушаем" диалог на предмет новых сообщений
        :param event: VkBotMessageEvent object
        :return: None
        """

        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info('Чат-бот не умеет обрабатывать события такого типа: %s', event.type)
            return

        user_id = event.message.peer_id
        text = event.message.text

        # search intent
        for intent in settings.INTENTS:
            log.debug(f'User {user_id} gets {intent}')
            if any(token in text.lower() for token in intent['tokens']):
                # run intent
                if intent['answer']:
                    self.send_text(intent['answer'], user_id)
                else:
                    if intent["name"] == "Случайные анекдоты":
                        self.random_jokes(user_id)
                    elif intent["name"] == "Анекдоты от Эльнура":
                        self.elnur_joke(user_id)
                    else:
                        self.best_jokes(user_id)
                break
        else:
            self.send_text(settings.DEFAULT_ANSWER, user_id)

    def best_jokes(self, user_id):
        """
        На сайте заходим в раздел лучших анекдотов, парсим один из 30 анекдотов и отправляем юзеру.
        :param user_id: id_usera который отправил нам сообщение
        """
        self.send_text('Введите число от 1 до 30', user_id)
        for event in self.long_poller.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                joke_number = event.message.text
                if handlers.best_joke_handler(joke_number):
                    best_joke_url = requests.get(f'https://baneks.ru/top')
                    if best_joke_url.status_code == 200:
                        html_doc = BeautifulSoup(best_joke_url.text, features='html.parser')
                        joke = html_doc.find_all("a")
                        best_joke = joke[int(joke_number)].text
                        self.send_joke(best_joke, user_id)
                        break
                else:
                    self.send_text('Нужно ввести число от 1 до 30. Че не понятно?', user_id)

    def random_jokes(self, user_id):
        """
        Выбираем случайный анекдот с сайта, парсим его и отправляем юзеру.
        :param user_id:
        """
        joke_number = randint(1, 1142)

        response = requests.get(f'https://baneks.ru/{joke_number}')

        if response.status_code == 200:
            html_doc = BeautifulSoup(response.text, features='html.parser')
            random_joke = html_doc.find('p').text
            random_joke = random_joke.replace('\n\n', '\n')
            self.send_joke(random_joke, user_id)

    def elnur_joke(self, user_id):
        """
        Вытаскиваем случайный анекдот из БД и отправляем юзеру.
        """
        elnur_joke = get_joke()
        self.send_joke(elnur_joke, user_id)

    def send_text(self, text_to_send, user_id):
        """
        Отправляем сообщение
        :param text_to_send: Текст, который отправляется
        :param user_id: Id пользователя, которому отправляем
        """
        self.api.messages.send(
            message=text_to_send,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id,
        )

    def send_joke(self, text_to_send, user_id):
        """
        Отправка анекдота с прикреплением случайной картинки.
        """
        image = get_photo()
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)

        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'

        self.api.messages.send(
            message=text_to_send,
            attachment=attachment,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id,
        )


if __name__ == '__main__':
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()
