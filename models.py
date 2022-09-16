from pony.orm import Database, Required, PrimaryKey, db_session, select
from settings import DB_CONFIG
from io import BytesIO
from PIL import Image

db = Database()

db.bind(**DB_CONFIG)


class Elnur_Jokes(db.Entity):
    """
    Подключение к таблице с анекдота от Эльнура
    """
    id_joke = PrimaryKey(int, auto=True)
    joke = Required(str)


class Photos(db.Entity):
    """
    Подключение к таблице со ссылками на картинки
    """
    id_photo = PrimaryKey(int, auto=True)
    path_photo = Required(str)


db.generate_mapping(create_tables=False)


@db_session
def get_joke():
    """
    Вытаскиваем из БД случаный анекдот
    """
    elnur_joke = select(e.joke for e in Elnur_Jokes).random(1)[0]

    return elnur_joke


@db_session
def get_photo():
    """
    Выстаскиваем из БД ссылку на случайную картинку
    """
    photo = select(p.path_photo for p in Photos).random(1)[0]

    base = Image.open(photo)

    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)

    return temp_file

