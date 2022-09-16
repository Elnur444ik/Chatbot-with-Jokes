"""
Handler - функция, которая принимает на вход число, а возвращает bool:
True если оно удовлетворяет условиям, False если данные введены неправильно.
"""


def best_joke_handler(number):
    try:
        if int(number) in range(1, 31):
            return True
        else:
            return False
    except ValueError:
        return False
