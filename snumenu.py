import datetime
import sys
import tomllib

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from PySide6 import QtCore, QtWidgets

class MenuManager:
    def __init__(self, config):
        self.urls = [
            'https://snuco.snu.ac.kr/foodmenu/',
            'https://snudorm.snu.ac.kr/foodmenu/',
        ]

        self.favorite = []
        self.excluded = []
        if config:
            if 'favorite' in config:
                self.favorite = config['favorite']
            if 'excluded' in config:
                self.excluded = config['excluded']

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

        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(*[self.fetch(session, url) for url in urls])
            return results

    async def fetch(self, session, url):
        async with session.get(url) as response:
            text = await response.text()
            return self.parse_html(text)

    def parse_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        title = soup.select('.title')[1:]
        breakfast = soup.select('.breakfast')[1:]
        lunch = soup.select('.lunch')[1:]
        dinner = soup.select('.dinner')[1:]

        menu = {}
        for i in range(len(title)):
            restaurant = title[i].text.split('(')[0].strip()
            if restaurant in self.favorite:
                old_menu = menu
                menu = {restaurant: {
                    'favorite': True,
                    'breakfast': breakfast[i].text.strip(),
                    'lunch': lunch[i].text.strip(),
                    'dinner': dinner[i].text.strip(),
                }}
                menu.update(old_menu)
            elif restaurant in self.excluded:
                continue
            else:
                menu[restaurant] = {
                    'favorite': False,
                    'breakfast': breakfast[i].text.strip(),
                    'lunch': lunch[i].text.strip(),
                    'dinner': dinner[i].text.strip(),
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
        return date, 'breakfast'
    elif hour < 15:
        return date, 'lunch'
    elif hour < 20:
        return date, 'dinner'
    else:
        return date + datetime.timedelta(days=1), 'breakfast'

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
        self.date_layout = QtWidgets.QVBoxLayout()
        self.date_layout.addWidget(self.date_text)

        self.datebutton_layout = QtWidgets.QHBoxLayout()
        self.datebutton_layout.addWidget(self.left_button)
        self.datebutton_layout.addWidget(self.date_text)
        self.datebutton_layout.addWidget(self.right_button)

    def init_meal_layout(self):
        self.breakfast_button = QtWidgets.QPushButton('아침')
        self.breakfast_button.clicked.connect(self.gen_meal_slot('breakfast'))
        self.lunch_button = QtWidgets.QPushButton('점심')
        self.lunch_button.clicked.connect(self.gen_meal_slot('lunch'))
        self.dinner_button = QtWidgets.QPushButton('저녁')
        self.dinner_button.clicked.connect(self.gen_meal_slot('dinner'))

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

            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.HLine)
            separator.setFrameShadow(QtWidgets.QFrame.Sunken)
            self.scroll_layout.addWidget(separator)

        num_widgets = self.scroll_layout.count()
        if num_widgets > 0:
            self.scroll_layout.itemAt(num_widgets - 1).widget().deleteLater()

    def clear_scroll_layout(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
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
