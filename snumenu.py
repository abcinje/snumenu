import asyncio
import datetime
import sys
import tomllib
from enum import StrEnum

import aiohttp
from bs4 import BeautifulSoup
from PySide6 import QtCore, QtWidgets

class Meal(StrEnum):
    BREAKFAST = 'breakfast'
    LUNCH = 'lunch'
    DINNER = 'dinner'

class MenuManager:
    def __init__(self, config):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/150.0.0.0 Safari/537.36",
        }

        self.urls = [
            'https://snuco.snu.ac.kr/foodmenu/',
            'https://snudorm.snu.ac.kr/foodmenu/',
        ]

        config = config or {}
        self.favorite = set(config.get('favorite', []))
        self.excluded = set(config.get('excluded', []))

        self.menu_dict = {}

    def get_menu(self, date, prefetch: int = 0):
        try:
            return self.menu_dict[date]
        except KeyError:
            results = asyncio.run(self.fetch_all(date, prefetch))
            num_urls = len(self.urls)
            for i in range(prefetch + 1):
                for j in range(num_urls):
                    try:
                        self.menu_dict[date + datetime.timedelta(days=i)].update(results[num_urls * i + j])
                    except KeyError:
                        self.menu_dict[date + datetime.timedelta(days=i)] = results[num_urls * i + j]
            return self.menu_dict[date]

    async def fetch_all(self, date, prefetch):
        urls = []
        num_urls = len(self.urls)
        for i in range(prefetch + 1):
            for j in range(num_urls):
                urls.append(self.urls[j] + '?date=' + str(date + datetime.timedelta(days=i)))

        async with aiohttp.ClientSession(headers=self.headers) as session:
            results = await asyncio.gather(*[self.fetch(session, url) for url in urls])
            return results

    async def fetch(self, session, url):
        async with session.get(url) as response:
            text = await response.text()
            return self.parse_html(text)

    def parse_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        title = soup.select('.title')[1:]
        meals = {meal: soup.select(f'.{meal}')[1:] for meal in Meal}

        menu = {}
        for i in range(len(title)):
            restaurant = title[i].text.split('(')[0].strip()
            if restaurant in self.favorite:
                old_menu = menu
                menu = {restaurant: {
                    'favorite': True,
                    **{meal: meals[meal][i].text.strip() for meal in Meal},
                }}
                menu.update(old_menu)
            elif restaurant in self.excluded:
                continue
            else:
                menu[restaurant] = {
                    'favorite': False,
                    **{meal: meals[meal][i].text.strip() for meal in Meal},
                }
        return menu

def get_date_str(date):
    timedelta = date - datetime.date.today()
    timedelta_str = ''
    if timedelta.days in range(-2, 3):
        timedelta_str = '\n' + ['그저께', '어제', '오늘', '내일', '모레'][timedelta.days + 2]

    day_of_the_week = '월화수목금토일'[date.weekday()]
    return f'{date.month}월 {date.day}일 ({day_of_the_week}){timedelta_str}'

def get_meal():
    date = datetime.date.today()
    hour = datetime.datetime.now().hour
    if hour < 10:
        return date, Meal.BREAKFAST
    elif hour < 15:
        return date, Meal.LUNCH
    elif hour < 20:
        return date, Meal.DINNER
    else:
        return date + datetime.timedelta(days=1), Meal.BREAKFAST

class MenuWidget(QtWidgets.QWidget):
    def __init__(self, config):
        super().__init__()

        self.manager = MenuManager(config)

        self.date, self.meal = get_meal()
        self.menu = self.manager.get_menu(self.date, prefetch=2)

        self.init_date_layout()
        self.init_meal_layout()
        self.init_scroll_widget()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.datebutton_layout)
        self.layout.addLayout(self.mealbutton_layout)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)

    def init_date_layout(self):
        self.left_button = QtWidgets.QPushButton('◀')
        self.left_button.clicked.connect(self.gen_date_slot(datetime.timedelta(days=-1)))
        self.right_button = QtWidgets.QPushButton('▶')
        self.right_button.clicked.connect(self.gen_date_slot(datetime.timedelta(days=1)))

        self.date_text = QtWidgets.QLabel(get_date_str(self.date), alignment=QtCore.Qt.AlignCenter)

        self.datebutton_layout = QtWidgets.QHBoxLayout()
        self.datebutton_layout.addWidget(self.left_button)
        self.datebutton_layout.addWidget(self.date_text)
        self.datebutton_layout.addWidget(self.right_button)

    def init_meal_layout(self):
        self.breakfast_button = QtWidgets.QPushButton('아침')
        self.breakfast_button.clicked.connect(self.gen_meal_slot(Meal.BREAKFAST))
        self.lunch_button = QtWidgets.QPushButton('점심')
        self.lunch_button.clicked.connect(self.gen_meal_slot(Meal.LUNCH))
        self.dinner_button = QtWidgets.QPushButton('저녁')
        self.dinner_button.clicked.connect(self.gen_meal_slot(Meal.DINNER))

        self.mealbutton_layout = QtWidgets.QHBoxLayout()
        self.mealbutton_layout.addWidget(self.breakfast_button)
        self.mealbutton_layout.addWidget(self.lunch_button)
        self.mealbutton_layout.addWidget(self.dinner_button)

    def init_scroll_widget(self):
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.fill_scroll_layout()

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setLayout(self.scroll_layout)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.scroll_content)

    def gen_date_slot(self, timedelta):
        @QtCore.Slot()
        def slot():
            self.date += timedelta
            self.menu = self.manager.get_menu(self.date)
            self.date_text.setText(get_date_str(self.date))

            self.clear_scroll_layout()
            self.fill_scroll_layout()
        return slot

    def gen_meal_slot(self, meal):
        @QtCore.Slot()
        def slot():
            self.meal = meal

            self.clear_scroll_layout()
            self.fill_scroll_layout()
        return slot

    def fill_scroll_layout(self):
        for restaurant, menu in self.menu.items():
            m = menu[self.meal]
            if not m:
                continue

            if self.scroll_layout.count() > 0:
                separator = QtWidgets.QFrame()
                separator.setFrameShape(QtWidgets.QFrame.HLine)
                separator.setFrameShadow(QtWidgets.QFrame.Sunken)
                self.scroll_layout.addWidget(separator)

            if menu['favorite']:
                restaurant += ' ★'
            label = QtWidgets.QLabel(restaurant, wordWrap=True)
            font = label.font()
            font.setBold(True)
            font.setPointSize(18)
            label.setFont(font)
            self.scroll_layout.addWidget(label)

            label = QtWidgets.QLabel(m, wordWrap=True)
            self.scroll_layout.addWidget(label)

    def clear_scroll_layout(self):
        while (item := self.scroll_layout.takeAt(0)) is not None:
            if widget := item.widget():
                widget.deleteLater()

def main():
    try:
        with open('config.toml', 'rb') as config_file:
            config = tomllib.load(config_file)
    except FileNotFoundError:
        config = None

    app = QtWidgets.QApplication([])

    widget = MenuWidget(config)
    widget.resize(360, 800)
    widget.setWindowTitle("SNUMenu")
    widget.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
