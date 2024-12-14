import datetime
import sys

import requests
from bs4 import BeautifulSoup
from PySide6 import QtCore, QtWidgets

favorite = ['302동식당 (880-1939)']
excluded = ['공대간이식당 (889-8956)', '75-1동 4층 푸드코트', '301동식당 (889-8955)', '220동식당 (887-1123)']

def get_meal():
    hour = datetime.datetime.now().hour
    if hour < 10:
        return 'breakfast'
    elif hour < 15:
        return 'lunch'
    elif hour < 20:
        return 'dinner'
    else:
        return 'breakfast'

def get_menu(date):
    snuco_url = 'https://snuco.snu.ac.kr/foodmenu/?date=' + str(date)
    snudorm_url = 'https://snudorm.snu.ac.kr/foodmenu/?date=' + str(date)

    menu = {}
    for url in [snuco_url, snudorm_url]:
        response = requests.get(url, verify=False)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        title = soup.select('.title')[1:]
        breakfast = soup.select('.breakfast')[1:]
        lunch = soup.select('.lunch')[1:]
        dinner = soup.select('.dinner')[1:]

        for i in range(len(title)):
            restaurant = title[i].text.strip()
            if restaurant in favorite:
                old_menu = menu
                menu = {restaurant: {
                    'breakfast': breakfast[i].text.strip(),
                    'lunch': lunch[i].text.strip(),
                    'dinner': dinner[i].text.strip(),
                }}
                menu.update(old_menu)
            elif restaurant in excluded:
                continue
            else:
                menu[restaurant] = {
                    'breakfast': breakfast[i].text.strip(),
                    'lunch': lunch[i].text.strip(),
                    'dinner': dinner[i].text.strip(),
                }
    return menu

def get_menu_str(menu_dict, meal):
    text = ''
    for restaurant, restaurant_menu in menu_dict.items():
        menu = restaurant_menu[meal]
        if not menu or '휴점' in menu:
            continue
        text += restaurant + '\n' + menu + '\n\n'
    return text

class MenuWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.date = datetime.date.today()
        self.meal = get_meal()
        campus_menu = get_menu(self.date)
        text = get_menu_str(campus_menu, self.meal)

        self.left_button = QtWidgets.QPushButton('◀')
        self.left_button.clicked.connect(self.left)
        self.right_button = QtWidgets.QPushButton('▶')
        self.right_button.clicked.connect(self.right)

        self.date_text = QtWidgets.QLabel(str(self.date), alignment=QtCore.Qt.AlignCenter)
        self.date_layout = QtWidgets.QVBoxLayout()
        self.date_layout.addWidget(self.date_text)
        self.date_groupbox = QtWidgets.QGroupBox()
        self.date_groupbox.setLayout(self.date_layout)

        self.datebutton_layout = QtWidgets.QHBoxLayout()
        self.datebutton_layout.addWidget(self.left_button)
        self.datebutton_layout.addWidget(self.date_groupbox)
        self.datebutton_layout.addWidget(self.right_button)

        self.breakfast_button = QtWidgets.QPushButton('아침')
        self.breakfast_button.clicked.connect(self.breakfast)
        self.lunch_button = QtWidgets.QPushButton('점심')
        self.lunch_button.clicked.connect(self.lunch)
        self.dinner_button = QtWidgets.QPushButton('저녁')
        self.dinner_button.clicked.connect(self.dinner)

        self.mealbutton_layout = QtWidgets.QHBoxLayout()
        self.mealbutton_layout.addWidget(self.breakfast_button)
        self.mealbutton_layout.addWidget(self.lunch_button)
        self.mealbutton_layout.addWidget(self.dinner_button)

        self.text = QtWidgets.QLabel(text, wordWrap=True)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidget(self.text)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.datebutton_layout)
        self.layout.addLayout(self.mealbutton_layout)
        self.layout.addWidget(self.scroll)

        self.setLayout(self.layout)

    @QtCore.Slot()
    def left(self):
        self.date -= datetime.timedelta(days=1)
        self.update_menu()

    @QtCore.Slot()
    def right(self):
        self.date += datetime.timedelta(days=1)
        self.update_menu()

    @QtCore.Slot()
    def breakfast(self):
        self.meal = 'breakfast'
        self.update_menu()

    @QtCore.Slot()
    def lunch(self):
        self.meal = 'lunch'
        self.update_menu()

    @QtCore.Slot()
    def dinner(self):
        self.meal = 'dinner'
        self.update_menu()

    def update_menu(self):
        menu = get_menu(self.date)
        text = get_menu_str(menu, self.meal)
        self.date_text.setText(str(self.date))
        self.text.setText(text)

def main():
    app = QtWidgets.QApplication([])

    widget = MenuWidget()
    widget.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
