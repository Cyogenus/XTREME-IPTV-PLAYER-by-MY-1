import sys
import os
import time
import requests
import subprocess
import configparser
import re
import json
import qdarkstyle
import html
import os
import ssl
import urllib.request
from PyQt5 import QtCore
from PyQt5.QtWidgets import QToolTip
from pathlib import Path
from lxml import etree
from datetime import datetime
from dateutil import parser, tz
import xml.etree.ElementTree as ET
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QDir
)
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QListWidget, QWidget, QFileDialog, QCheckBox, QSizePolicy, QHBoxLayout,
    QDialog, QFormLayout, QDialogButtonBox, QTabWidget, QListWidgetItem,
    QSpinBox, QMenu, QAction, QTextEdit, 
)

is_windows = sys.platform.startswith('win')
is_mac = sys.platform.startswith('darwin')
is_linux = sys.platform.startswith('linux')

# EPG Cache File
cache_file = Path.home() / '.iptv' / 'epg_cache1.xml'
os.makedirs(cache_file.parent, exist_ok=True)

CUSTOM_USER_AGENT = (
    "Connection: Keep-Alive User-Agent: okhttp/5.0.0-alpha.2 "
    "Accept-Encoding: gzip, deflate"
)

def normalize_channel_name(name):
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\b(hd|sd|channel|tv)\b', '', name)
    name = name.strip()
    return name

class EPGWorkerSignals(QObject):
    finished = pyqtSignal(dict, dict)
    error = pyqtSignal(str)

class EPGWorker(QRunnable):
    def __init__(self, server, username, password, http_method):
        super().__init__()
        self.server = server
        self.username = username
        self.password = password
        self.http_method = http_method
        self.signals = EPGWorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            cache_file = 'epg_cache1.xml'
            cache_valid = False
            if os.path.exists(cache_file):
                cache_age = time.time() - os.path.getmtime(cache_file)
                if cache_age < 3600:  
                    cache_valid = True

            if cache_valid:
                with open(cache_file, 'rb') as f:
                    epg_xml_data = f.read()
            else:
                epg_url = f"{self.server}/xmltv.php?username={self.username}&password={self.password}"
                headers = {'User-Agent': CUSTOM_USER_AGENT}
                if self.http_method == 'POST':
                    response = requests.post(epg_url, headers=headers, timeout=10)
                else:
                    response = requests.get(epg_url, headers=headers, timeout=10)
                response.raise_for_status()
                epg_xml_data = response.content
                with open(cache_file, 'wb') as f:
                    f.write(epg_xml_data)

            epg_data, channel_id_to_names = self.parse_epg_data(epg_xml_data)
            self.signals.finished.emit(epg_data, channel_id_to_names)
        except Exception as e:
            self.signals.error.emit(str(e))

    def parse_epg_data(self, epg_xml_data):
        epg_dict = {}
        channel_id_to_names = {}
        try:
            epg_tree = ET.fromstring(epg_xml_data)
            for channel in epg_tree.findall('channel'):
                channel_id = channel.get('id')
                if channel_id:
                    channel_id = channel_id.strip().lower()
                    display_names = []
                    for display_name_elem in channel.findall('display-name'):
                        if display_name_elem.text:
                            display_name = display_name_elem.text.strip()
                            normalized_name = normalize_channel_name(display_name)
                            display_names.append(normalized_name)
                    channel_id_to_names[channel_id] = display_names

            for programme in epg_tree.findall('programme'):
                channel_id = programme.get('channel')
                if channel_id:
                    channel_id = channel_id.strip().lower()
                start_time = programme.get('start')
                stop_time = programme.get('stop')
                title_elem = programme.find('title')
                description_elem = programme.find('desc')

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ''
                description = description_elem.text.strip() if description_elem is not None and description_elem.text else ''

                epg_entry = {
                    'start_time': start_time,
                    'stop_time': stop_time,
                    'title': title,
                    'description': description
                }

                if channel_id not in epg_dict:
                    epg_dict[channel_id] = []
                epg_dict[channel_id].append(epg_entry)

            return epg_dict, channel_id_to_names

        except Exception as e:
            print(f"Error parsing EPG data: {e}")
            return {}, {}

class AddressBookDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Address Book")
        self.setMinimumSize(400, 300)
        self.parent = parent

        layout = QtWidgets.QVBoxLayout(self)
        self.credentials_list = QtWidgets.QListWidget()
        layout.addWidget(self.credentials_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder))
        self.select_button = QPushButton("Select")
        self.select_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        self.delete_button = QPushButton("Delete")
        self.delete_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton))
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)

        self.load_saved_credentials()

        self.add_button.clicked.connect(self.add_credentials)
        self.select_button.clicked.connect(self.select_credentials)
        self.delete_button.clicked.connect(self.delete_credentials)
        self.credentials_list.itemDoubleClicked.connect(self.double_click_credentials)

    def load_saved_credentials(self):
        self.credentials_list.clear()
        config = configparser.ConfigParser()
        config.read('credentials.ini')
        if 'Credentials' in config:
            for key in config['Credentials']:
                self.credentials_list.addItem(key)

    def add_credentials(self):
        dialog = AddCredentialsDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            method, name, *credentials = dialog.get_credentials()
            if name:
                config = configparser.ConfigParser()
                config.read('credentials.ini')
                if 'Credentials' not in config:
                    config['Credentials'] = {}
                if method == 'manual':
                    server, username, password = credentials
                    config['Credentials'][name] = f"manual|{server}|{username}|{password}"
                elif method == 'm3u_plus':
                    m3u_url, = credentials
                    config['Credentials'][name] = f"m3u_plus|{m3u_url}"
                with open('credentials.ini', 'w') as config_file:
                    config.write(config_file)
                self.load_saved_credentials()

    def select_credentials(self):
        selected_item = self.credentials_list.currentItem()
        if selected_item:
            name = selected_item.text()
            config = configparser.ConfigParser()
            config.read('credentials.ini')
            if 'Credentials' in config and name in config['Credentials']:
                data = config['Credentials'][name]
                if data.startswith('manual|'):
                    _, server, username, password = data.split('|')
                    self.parent.server_entry.setText(server)
                    self.parent.username_entry.setText(username)
                    self.parent.password_entry.setText(password)
                    self.parent.login()
                elif data.startswith('m3u_plus|'):
                    _, m3u_url = data.split('|', 1)
                    self.parent.extract_credentials_from_m3u_plus_url(m3u_url)
                    self.parent.login()
                self.accept()

    def double_click_credentials(self, item):
        self.select_credentials()
        self.accept()

    def delete_credentials(self):
        selected_item = self.credentials_list.currentItem()
        if selected_item:
            name = selected_item.text()
            config = configparser.ConfigParser()
            config.read('credentials.ini')
            if 'Credentials' in config and name in config['Credentials']:
                del config['Credentials'][name]
                with open('credentials.ini', 'w') as config_file:
                    config.write(config_file)
                self.load_saved_credentials()

class AddCredentialsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Credentials")
        layout = QtWidgets.QVBoxLayout(self)

        self.method_selector = QtWidgets.QComboBox()
        self.method_selector.addItems(["Manual Entry", "m3u_plus URL Entry"])
        layout.addWidget(QtWidgets.QLabel("Select Method:"))
        layout.addWidget(self.method_selector)

        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        self.manual_form = QtWidgets.QWidget()
        manual_layout = QFormLayout(self.manual_form)
        self.name_entry_manual = QLineEdit()
        self.server_entry = QLineEdit()
        self.username_entry = QLineEdit()
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        manual_layout.addRow("Name:", self.name_entry_manual)
        manual_layout.addRow("Server URL:", self.server_entry)
        manual_layout.addRow("Username:", self.username_entry)
        manual_layout.addRow("Password:", self.password_entry)

        self.m3u_form = QtWidgets.QWidget()
        m3u_layout = QFormLayout(self.m3u_form)
        self.name_entry_m3u = QLineEdit()
        self.m3u_url_entry = QLineEdit()
        m3u_layout.addRow("Name:", self.name_entry_m3u)
        m3u_layout.addRow("m3u_plus URL:", self.m3u_url_entry)

        self.stack.addWidget(self.manual_form)
        self.stack.addWidget(self.m3u_form)

        self.method_selector.currentIndexChanged.connect(self.stack.setCurrentIndex)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)

    def validate_and_accept(self):
        method = self.method_selector.currentText()
        if method == "Manual Entry":
            name = self.name_entry_manual.text().strip()
            server = self.server_entry.text().strip()
            username = self.username_entry.text().strip()
            password = self.password_entry.text().strip()
            if not name or not server or not username or not password:
                QtWidgets.QMessageBox.warning(self, "Input Error", "Please fill all fields for Manual Entry.")
                return
            self.accept()
        else:
            name = self.name_entry_m3u.text().strip()
            m3u_url = self.m3u_url_entry.text().strip()
            if not name or not m3u_url:
                QtWidgets.QMessageBox.warning(self, "Input Error", "Please fill all fields for m3u_plus URL Entry.")
                return
            self.accept()

    def get_credentials(self):
        method = self.method_selector.currentText()
        if method == "Manual Entry":
            name = self.name_entry_manual.text().strip()
            server = self.server_entry.text().strip()
            username = self.username_entry.text().strip()
            password = self.password_entry.text().strip()
            return ('manual', name, server, username, password)
        else:
            name = self.name_entry_m3u.text().strip()
            m3u_url = self.m3u_url_entry.text().strip()
            return ('m3u_plus', name, m3u_url)

class IPTVPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xtream IPTV Player by MY-1 V4.0")
        self.resize(700, 550)

        self.groups = {}
        self.entries_per_tab = {
            'LIVE': [],
            'Movies': [],
            'Series': []
        }
        self.navigation_stacks = {
            'LIVE': [],
            'Movies': [],
            'Series': []
        }
        self.external_player_command = ""
        self.load_external_player_command()

        self.top_level_scroll_positions = {
            'LIVE': 0,
            'Movies': 0,
            'Series': 0
        }

        self.server = ""
        self.username = ""
        self.password = ""
        self.login_type = None  
        self.epg_data = {}  
        self.channel_id_to_names = {}  
        self.epg_last_updated = None  
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(10)
        self.epg_id_mapping = {}
        self.epg_name_map = {}
        

        self.go_back_icon = self.style().standardIcon(QtWidgets.QStyle.SP_ArrowBack)
        self.live_channel_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolume)
        self.movies_channel_icon = self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
        self.series_channel_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(15)

        self.server_label = QLabel("Server URL:")
        self.server_label.setFixedWidth(53)
        self.server_entry = QLineEdit()
        self.server_entry.setPlaceholderText("Enter Server URL...")
        self.server_entry.setClearButtonEnabled(True)

        self.username_label = QLabel("Username:")
        self.username_label.setFixedWidth(50)
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Enter Username...")
        self.username_entry.setClearButtonEnabled(True)

        self.password_label = QLabel("Password:")
        self.password_label.setFixedWidth(50)
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("Enter Password...")
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.password_entry.setClearButtonEnabled(True)

        row1_layout.addWidget(self.server_label)
        row1_layout.addWidget(self.server_entry)
        row1_layout.addWidget(self.username_label)
        row1_layout.addWidget(self.username_entry)
        row1_layout.addWidget(self.password_label)
        row1_layout.addWidget(self.password_entry)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        self.login_button = QPushButton("Login")
        self.login_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        self.login_button.clicked.connect(self.login)

        self.m3u_plus_button = QPushButton("M3u_plus")
        search_icon = QIcon.fromTheme("edit-find")
        if search_icon.isNull():
            search_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        self.m3u_plus_button.setIcon(search_icon)
        self.m3u_plus_button.clicked.connect(self.open_m3u_plus_dialog)

        self.address_book_button = QPushButton("Address Book")
        self.address_book_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        self.address_book_button.setToolTip("Manage Saved Credentials")
        self.address_book_button.clicked.connect(self.open_address_book)

        self.choose_player_button = QPushButton("Choose Media Player")
        self.choose_player_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.choose_player_button.clicked.connect(self.choose_external_player)

        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.m3u_plus_button)
        buttons_layout.addWidget(self.address_book_button)
        buttons_layout.addWidget(self.choose_player_button)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignRight)
        checkbox_layout.setSpacing(15)

        self.http_method_checkbox = QCheckBox("Use POST Method")
        self.http_method_checkbox.setToolTip("Check to use POST instead of GET for server requests")
        checkbox_layout.addWidget(self.http_method_checkbox)

        self.keep_on_top_checkbox = QCheckBox("Keep on top")
        self.keep_on_top_checkbox.setToolTip("Keep the application on top of all windows")
        self.keep_on_top_checkbox.stateChanged.connect(self.toggle_keep_on_top)
        checkbox_layout.addWidget(self.keep_on_top_checkbox)

        self.epg_checkbox = QCheckBox("Download EPG")
        self.epg_checkbox.setToolTip("Check to download EPG data for channels")
        self.epg_checkbox.stateChanged.connect(self.on_epg_checkbox_toggled)
        checkbox_layout.addWidget(self.epg_checkbox)

        # **Add Dark Theme Checkbox**
        self.dark_theme_checkbox = QCheckBox("Dark Theme")
        self.dark_theme_checkbox.setToolTip("Enable or disable dark theme")
        self.dark_theme_checkbox.stateChanged.connect(self.toggle_dark_theme)
        checkbox_layout.addWidget(self.dark_theme_checkbox)

        self.font_size_label = QLabel("Font Size:")
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 24)
        self.font_size_spinbox.setValue(10)
        self.font_size_spinbox.setToolTip("Set the font size for playlist items")
        self.font_size_spinbox.valueChanged.connect(self.update_font_size)
        self.font_size_spinbox.setFixedWidth(60)

        self.default_font_size = 10
        checkbox_layout.addWidget(self.font_size_label)
        checkbox_layout.addWidget(self.font_size_spinbox)

        controls_layout.addLayout(row1_layout)
        controls_layout.addLayout(buttons_layout)
        controls_layout.addLayout(checkbox_layout)

        main_layout.addLayout(controls_layout)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)

        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget)

        self.tab_icon_size = QSize(24, 24)
        live_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolume)
        movies_icon = self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
        series_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)

        self.live_tab = QWidget()
        self.movies_tab = QWidget()
        self.series_tab = QWidget()

        self.tab_widget.addTab(self.live_tab, live_icon, "LIVE")
        self.tab_widget.addTab(self.movies_tab, movies_icon, "Movies")
        self.tab_widget.addTab(self.series_tab, series_icon, "Series")

        self.live_layout = QVBoxLayout(self.live_tab)
        self.movies_layout = QVBoxLayout(self.movies_tab)
        self.series_layout = QVBoxLayout(self.series_tab)

        self.search_bar_live = QLineEdit()
        self.search_bar_live.setPlaceholderText("Search Live Channels...")
        self.search_bar_live.setClearButtonEnabled(True)
        self.add_search_icon(self.search_bar_live)
        self.search_bar_live.textChanged.connect(lambda text: self.search_in_list('LIVE', text))

        self.search_bar_movies = QLineEdit()
        self.search_bar_movies.setPlaceholderText("Search Movies...")
        self.search_bar_movies.setClearButtonEnabled(True)
        self.add_search_icon(self.search_bar_movies)
        self.search_bar_movies.textChanged.connect(lambda text: self.search_in_list('Movies', text))

        self.search_bar_series = QLineEdit()
        self.search_bar_series.setPlaceholderText("Search Series...")
        self.search_bar_series.setClearButtonEnabled(True)
        self.add_search_icon(self.search_bar_series)
        self.search_bar_series.textChanged.connect(lambda text: self.search_in_list('Series', text))

        self.add_search_bar(self.live_layout, self.search_bar_live)
        self.add_search_bar(self.movies_layout, self.search_bar_movies)
        self.add_search_bar(self.series_layout, self.search_bar_series)

        self.channel_list_live = QListWidget()
        self.channel_list_movies = QListWidget()
        self.channel_list_series = QListWidget()
        
        
        standard_icon_size = QSize(24, 24)

        # 🟢 Install event filter for tooltip detection
        for widget in [self.channel_list_live, self.channel_list_movies, self.channel_list_series]:
            widget.viewport().installEventFilter(self)
        
        
        for list_widget in [self.channel_list_live, self.channel_list_movies, self.channel_list_series]:
            list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            list_widget.setIconSize(standard_icon_size)
            list_widget.setStyleSheet("""
                QListWidget::item {
                    padding-top: 5px;
                    padding-bottom: 5px;
                }
            """)
        
        self.live_layout.addWidget(self.channel_list_live)
        self.movies_layout.addWidget(self.channel_list_movies)
        self.series_layout.addWidget(self.channel_list_series)

        self.list_widgets = {
            'LIVE': self.channel_list_live,
            'Movies': self.channel_list_movies,
            'Series': self.channel_list_series,
        }
        
        self.tab_widget.currentChanged.connect(self.on_tab_change)
        self.channel_list_live.itemDoubleClicked.connect(self.channel_item_double_clicked)
        self.channel_list_movies.itemDoubleClicked.connect(self.channel_item_double_clicked)
        self.channel_list_series.itemDoubleClicked.connect(self.channel_item_double_clicked)

        self.info_tab = QWidget()
        self.info_tab_layout = QVBoxLayout(self.info_tab)
        self.result_display = QTextEdit(self.info_tab)
        self.result_display.setReadOnly(True)
        default_font = QFont()
        default_font.setPointSize(self.default_font_size)
        self.result_display.setFont(default_font)
        self.info_tab_layout.addWidget(self.result_display)
        info_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
        self.tab_widget.addTab(self.info_tab, info_icon, "Info")
        self.info_tab_initialized = False

        main_layout.addWidget(content_widget)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.playlist_progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.playlist_progress_animation.setDuration(1000)  # longer duration for smoother animation
        self.playlist_progress_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.load_theme_preference()

    

    def toggle_dark_theme(self, state):
        """
        Toggle the application's dark theme based on the checkbox state.
        Keeps your existing save_theme_preference calls and simply augments
        the stylesheet with tooltip styles.
        """
        app = QApplication.instance()

        # Try both qdarkstyle loaders for compatibility
        def _load_qdarkstyle():
            try:
                return qdarkstyle.load_stylesheet_pyqt5()
            except Exception:
                try:
                    return qdarkstyle.load_stylesheet(qt_api='pyqt5')
                except Exception:
                    return ""

        if state == Qt.Checked:
            base = _load_qdarkstyle()
            app.setStyleSheet(base + """
            /* Tooltip in dark */
            QToolTip {
                padding: 6px 8px;
                border: 1px solid #1aa3b5;
                background: #1b2332;
                color: #e3f6ff;
                font-size: 12px;
            }
            """)
            self.save_theme_preference(dark=True)
        else:
            # Reset to light but keep a nicer tooltip style
            app.setStyleSheet("""
            QToolTip {
                padding: 6px 8px;
                border: 1px solid #888;
                background: #ffffff;
                color: #222;
                font-size: 12px;
            }
            """)
            self.save_theme_preference(dark=False)

            

    def load_theme_preference(self):
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        dark = False
        if 'Theme' in config:
            dark = config['Theme'].getboolean('Dark', fallback=False)
        if dark:
            self.dark_theme_checkbox.setChecked(True)
            QApplication.instance().setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            self.dark_theme_checkbox.setChecked(False)
            QApplication.instance().setStyleSheet("")

    def save_theme_preference(self, dark):
        """
        Save the theme preference to config.ini.
        """
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'Theme' not in config:
            config['Theme'] = {}
        config['Theme']['Dark'] = str(dark)
        with open('config.ini', 'w') as config_file:
            config.write(config_file)

    def add_search_icon(self, search_bar):
        search_icon = QIcon.fromTheme("edit-find")
        if search_icon.isNull():
            search_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        search_bar.addAction(search_icon, QLineEdit.LeadingPosition)

    def toggle_keep_on_top(self, state):
        flags = self.windowFlags()
        if state == Qt.Checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()


    def add_search_bar(self, layout, search_bar):
        layout.addWidget(search_bar)

    def get_http_method(self):
        return 'POST' if self.http_method_checkbox.isChecked() else 'GET'

    def make_request(self, method, url, params=None, timeout=10):
        headers = {'User-Agent': CUSTOM_USER_AGENT}
        if method == 'POST':
            return requests.post(url, data=params, headers=headers, timeout=timeout)
        else:
            return requests.get(url, params=params, headers=headers, timeout=timeout)

    def open_m3u_plus_dialog(self):
        text, ok = QtWidgets.QInputDialog.getText(self, 'M3u_plus Login', 'Enter m3u_plus URL:')
        if ok and text:
            m3u_plus_url = text.strip()
            self.extract_credentials_from_m3u_plus_url(m3u_plus_url)
            self.login()

    def update_font_size(self, value):
        self.default_font_size = value
        for tab_name, list_widget in self.list_widgets.items():
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                font = item.font()
                font.setPointSize(value)
                item.setFont(font)

        font = QFont()
        font.setPointSize(value)
        self.result_display.setFont(font)

    def extract_credentials_from_m3u_plus_url(self, url):
        try:
            pattern = r'(http[s]?://[^/]+)/get\.php\?username=([^&]*)&password=([^&]*)&type=(m3u_plus|m3u|&output=m3u8)'
            match = re.match(pattern, url)
            if match:
                self.server = match.group(1)
                self.username = match.group(2)
                self.password = match.group(3)
                self.server_entry.setText(self.server)
                self.username_entry.setText(self.username)
                self.password_entry.setText(self.password)
            else:
                self.animate_progress(0, 100, "Invalid m3u_plus or m3u URL")
        except Exception as e:
            print(f"Error extracting credentials: {e}")
            self.animate_progress(0, 100, "Error extracting credentials")

    def set_progress_text(self, text):
        self.progress_bar.setFormat(text)

    def animate_progress(self, start, end, text):
        self.playlist_progress_animation.stop()
        self.playlist_progress_animation.setStartValue(start)
        self.playlist_progress_animation.setEndValue(end)
        self.set_progress_text(text)
        self.playlist_progress_animation.start()

    def reset_progress_bar(self):
        self.playlist_progress_animation.stop()
        self.progress_bar.setValue(0)
        self.set_progress_text("")

    def login(self):
        # When logging into another server, reset the progress bar
        self.reset_progress_bar()
        self.epg_data = {}
        self.channel_id_to_names = {}
        self.epg_last_updated = None
        for tab_name, list_widget in self.list_widgets.items():
            list_widget.clear()

        cache_file = 'epg_cache1.xml'
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                print(f"Error deleting EPG cache: {e}")
                self.animate_progress(0, 100, "Error deleting EPG cache")
                return

        server = self.server_entry.text().strip()
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not server or not username or not password:
            self.animate_progress(0, 100, "Please fill all fields")
            return

        # Start loading playlist from 0 to 100
        self.reset_progress_bar()
        self.animate_progress(0, 30, "Loading playlist...")
        self.fetch_categories_only(server, username, password)

    def fetch_categories_only(self, server, username, password):
        try:
            http_method = self.get_http_method()

            params = {
                'username': username,
                'password': password,
                'action': 'get_live_categories'
            }

            categories_url = f"{server}/player_api.php"
            live_response = self.make_request(http_method, categories_url, params, timeout=10)
            live_response.raise_for_status()

            params['action'] = 'get_vod_categories'
            movies_response = self.make_request(http_method, categories_url, params, timeout=10)
            movies_response.raise_for_status()

            params['action'] = 'get_series_categories'
            series_response = self.make_request(http_method, categories_url, params, timeout=10)
            series_response.raise_for_status()

            self.groups = {
                "LIVE": live_response.json(),
                "Movies": movies_response.json(),
                "Series": series_response.json(),
            }
            self.server = server
            self.username = username
            self.password = password
            self.login_type = 'xtream'
            self.navigation_stacks = {'LIVE': [], 'Movies': [], 'Series': []}
            self.top_level_scroll_positions = {'LIVE': 0, 'Movies': 0, 'Series': 0}
            self.update_category_lists('LIVE')
            self.update_category_lists('Movies')
            self.update_category_lists('Series')
            self.fetch_additional_data(server, username, password)

            # Playlist loading complete
            self.animate_progress(self.progress_bar.value(), 100, "Playlist loaded")

            # After playlist is fully loaded, if EPG is checked and not loaded, load EPG now
            if self.epg_checkbox.isChecked() and not self.epg_data:
                # Reset to 0 before loading EPG
                self.reset_progress_bar()
                self.animate_progress(0, 50, "Loading EPG data...")
                self.load_epg_data_async()

        except requests.exceptions.Timeout:
            print("Request timed out")
            self.animate_progress(self.progress_bar.value(), 100, "Login timed out")
        except requests.RequestException as e:
            print(f"Network error: {e}")
            self.animate_progress(self.progress_bar.value(), 100, "Network Error")
        except ValueError as e:
            print(f"JSON decode error: {e}")
            self.animate_progress(self.progress_bar.value(), 100, "Invalid server response")
        except Exception as e:
            print(f"Error fetching categories: {e}")
            self.animate_progress(self.progress_bar.value(), 100, "Error fetching categories")

    def fetch_additional_data(self, server, username, password):
        try:
            if not server.startswith("http://") and not server.startswith("https://"):
                server = f"http://{server}"

            headers = {'User-Agent': CUSTOM_USER_AGENT}
            payload = {'username': username, 'password': password}
            url = f"{server}/player_api.php"

            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()

            additional_data = response.json()
            user_info = additional_data.get("user_info", {})
            server_info = additional_data.get("server_info", {})

            hostname = server_info.get("url", server.replace("http://", "").replace("https://", ""))
            port = server_info.get("port", 25461)
            host = f"http://{hostname}:{port}"

            username = user_info.get("username", "Unknown")
            password = user_info.get("password", "Unknown")
            max_connections = user_info.get("max_connections", "Unlimited")
            active_connections = user_info.get("active_cons", "0")
            trial = "Yes" if user_info.get("is_trial") == "1" else "No"
            expire_timestamp = user_info.get("exp_date")
            expiry = (
                datetime.fromtimestamp(int(expire_timestamp)).strftime("%B %d, %Y")
                if expire_timestamp else "Unlimited"
            )
            status = user_info.get("status", "Unknown")

            created_at_timestamp = user_info.get("created_at", "Unknown")
            created_at = (
                datetime.fromtimestamp(int(created_at_timestamp)).strftime("%B %d, %Y")
                if created_at_timestamp and created_at_timestamp.isdigit() else "Unknown"
            )
            timezone = server_info.get("timezone", "Unknown")

            formatted_data = (
                f"Host: {host}\n"
                f"Username: {username}\n"
                f"Password: {password}\n"
                f"Max Connections: {max_connections}\n"
                f"Active Connections: {active_connections}\n"
                f"Timezone: {timezone}\n"
                f"Trial: {trial}\n"
                f"Status: {status}\n"
                f"Created At: {created_at}\n"
                f"Expiry: {expiry}\n"
            )

            self.result_display.setText(formatted_data)
            self.info_tab_initialized = True

        except Exception as e:
            print(f"Error fetching additional data: {e}")

    def load_epg_data_async(self):
        if not self.server or not self.username or not self.password:
            # Can't load EPG if not logged in
            return
        http_method = self.get_http_method()
        epg_worker = EPGWorker(self.server, self.username, self.password, http_method)
        epg_worker.signals.finished.connect(self.on_epg_loaded)
        epg_worker.signals.error.connect(self.on_epg_error)
        self.threadpool.start(epg_worker)

    def on_epg_loaded(self, epg_data, channel_id_to_names):
        self.epg_data = epg_data
        self.channel_id_to_names = channel_id_to_names

        name_to_id = {}
        for cid, names in channel_id_to_names.items():
            for n in names:
                if n not in name_to_id:
                    name_to_id[n] = cid
        self.epg_name_map = name_to_id

        # EPG done
        self.animate_progress(self.progress_bar.value(), 100, "EPG data loaded")

    def on_epg_error(self, error_message):
        print(f"Error fetching EPG data: {error_message}")
        self.animate_progress(self.progress_bar.value(), 100, "Error fetching EPG data")

    def channel_item_double_clicked(self, item):
        try:
            sender = self.sender()
            category = {
                self.channel_list_live: 'LIVE',
                self.channel_list_movies: 'Movies',
                self.channel_list_series: 'Series'
            }.get(sender)

            if not category:
                return

            selected_item = sender.currentItem()
            if not selected_item:
                return

            selected_text = selected_item.text()
            list_widget = self.get_list_widget(category)
            current_scroll_position = list_widget.verticalScrollBar().value()
            stack = self.navigation_stacks[category]

            if stack:
                stack[-1]['scroll_position'] = current_scroll_position
            else:
                self.top_level_scroll_positions[category] = current_scroll_position

            self.handle_xtream_double_click(selected_item, selected_text, category, sender)

        except Exception as e:
            print(f"Error occurred while handling double click: {e}")

    def update_category_lists(self, tab_name):
        if tab_name == 'LIVE':
            self.search_bar_live.clear()
        elif tab_name == 'Movies':
            self.search_bar_movies.clear()
        elif tab_name == 'Series':
            self.search_bar_series.clear()

        try:
            list_widget = self.get_list_widget(tab_name)
            list_widget.clear()

            if self.navigation_stacks[tab_name]:
                go_back_item = QListWidgetItem("Go Back")
                go_back_item.setIcon(self.go_back_icon)
                list_widget.addItem(go_back_item)

            if tab_name == 'LIVE':
                channel_icon = self.live_channel_icon
            elif tab_name == 'Movies':
                channel_icon = self.movies_channel_icon
            elif tab_name == 'Series':
                channel_icon = self.series_channel_icon
            else:
                channel_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

            group_list = self.groups[tab_name]
            category_names = sorted(group["category_name"] for group in group_list)
            items = []
            for category_name in category_names:
                item = QListWidgetItem(category_name)
                item.setIcon(channel_icon)
                items.append(item)

            items.sort(key=lambda x: x.text())
            for item in items:
                list_widget.addItem(item)

            scroll_position = self.top_level_scroll_positions.get(tab_name, 0)
            list_widget.verticalScrollBar().setValue(scroll_position)
        except Exception as e:
            print(f"Error updating category lists: {e}")
            self.animate_progress(self.progress_bar.value(), 100, "Error updating lists")

        # ─── inside class IPTVPlayerApp ─────────────────────────────────────────────
    def fetch_channels(self, category_name, tab_name):
        """
        Retrieve the LIVE / VOD / Series list for the chosen category and show
        it.  No per-movie look-ups are performed here – we only get the list
        itself, add a playback URL, and store it on the navigation stack.
        """
        try:
            # 1. category_id for the clicked name --------------------------------
            category_id = next(
                g["category_id"] for g in self.groups[tab_name]
                if g["category_name"] == category_name
            )

            # remember scroll position before diving one level deeper -----------
            lw          = self.get_list_widget(tab_name)
            curr_scroll = lw.verticalScrollBar().value()
            if self.navigation_stacks[tab_name]:
                self.navigation_stacks[tab_name][-1]["scroll_position"] = curr_scroll
            else:
                self.top_level_scroll_positions[tab_name] = curr_scroll

            # 2. request the list ------------------------------------------------
            params = {
                "username":   self.username,
                "password":   self.password,
                "action":     "",
                "category_id": category_id,
            }
            if tab_name == "LIVE":
                params["action"] = "get_live_streams"
                stream_type      = "live"
            elif tab_name == "Movies":
                params["action"] = "get_vod_streams"
                stream_type      = "movie"
            else:  # Series tab
                params["action"] = "get_series"
                stream_type      = "series"

            response = self.make_request(
                self.get_http_method(),
                f"{self.server}/player_api.php",
                params, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Expected a list of entries")

            # 3. add playback URL and tidy epg_channel_id -----------------------
            for entry in data:
                sid = entry.get("stream_id")
                if sid:
                    if tab_name == "LIVE":
                        ext = "ts"
                    else:
                        ext = entry.get("container_extension", "m3u8")
                    entry["url"] = (f"{self.server}/{stream_type}/{self.username}/"
                                    f"{self.password}/{sid}.{ext}")
                epg_id = (entry.get("epg_channel_id") or "").strip().lower()
                entry["epg_channel_id"] = epg_id if epg_id else None


            # 4. push onto stack & display --------------------------------------
            self.entries_per_tab[tab_name] = data
            self.navigation_stacks[tab_name].append({
                "level": "channels",
                "data":  {"tab_name": tab_name, "entries": data},
                "scroll_position": 0
            })
            self.show_channels(lw, tab_name)

        except Exception as e:
            print("Error fetching channels:", e)
            self.animate_progress(self.progress_bar.value(), 100,
                                  "Error fetching channels")
    # ─────────────────────────────────────────────────────────────────────────────



    def handle_xtream_double_click(self, selected_item, selected_text, tab_name, sender):
        try:
            list_widget = self.get_list_widget(tab_name)
            stack = self.navigation_stacks[tab_name]

            if selected_text == "Go Back":
                if stack:
                    stack.pop()
                    if stack:
                        last_level = stack[-1]
                        level = last_level['level']
                        data = last_level['data']
                        scroll_position = last_level.get('scroll_position', 0)
                        if level == 'channels':
                            self.entries_per_tab[tab_name] = data['entries']
                            self.show_channels(list_widget, tab_name)
                            list_widget.verticalScrollBar().setValue(scroll_position)
                        elif level == 'series_categories':
                            self.show_series_in_category(data['series_list'], restore_scroll_position=True, scroll_position=scroll_position)
                        elif level == 'series':
                            self.show_seasons(data['seasons'], restore_scroll_position=True, scroll_position=scroll_position)
                        elif level == 'season':
                            self.show_episodes(data['episodes'], restore_scroll_position=True, scroll_position=scroll_position)
                    else:
                        self.update_category_lists(tab_name)
                        list_widget.verticalScrollBar().setValue(self.top_level_scroll_positions.get(tab_name, 0))
                else:
                    self.update_category_lists(tab_name)
                    list_widget.verticalScrollBar().setValue(self.top_level_scroll_positions.get(tab_name, 0))
                return

            if tab_name != "Series":
                if selected_text in [group["category_name"] for group in self.groups[tab_name]]:
                    self.fetch_channels(selected_text, tab_name)
                else:
                    selected_entry = selected_item.data(Qt.UserRole)
                    if selected_entry and "url" in selected_entry:
                        self.play_channel(selected_entry)
                return

            # Series logic
            if tab_name == "Series":
                if not stack:
                    if selected_text in [group["category_name"] for group in self.groups["Series"]]:
                        self.fetch_series_in_category(selected_text)
                        return
                elif stack[-1]['level'] == 'series_categories':
                    series_entry = selected_item.data(Qt.UserRole)
                    if series_entry and "series_id" in series_entry:
                        self.fetch_seasons(series_entry)
                        return
                elif stack[-1]['level'] == 'series':
                    season_number = selected_item.data(Qt.UserRole)
                    series_entry = stack[-1]['data']['series_entry']
                    self.fetch_episodes(series_entry, season_number)
                    return
                elif stack[-1]['level'] == 'season':
                    selected_entry = selected_item.data(Qt.UserRole)
                    if selected_entry and "url" in selected_entry:
                        self.play_channel(selected_entry)
                    return

        except Exception as e:
            print(f"Error loading channels: {e}")


    def fetch_tmdb_description(self, tmdb_id, media_hint=None):
        """
        Scrape basic info (title / description / rating / year) from TMDb.
        Tries the 'movie' page first; if it 404s, tries the 'tv' page.
        The result – or an empty dict on failure – is cached in self.tmdb_cache.
        """
        import ssl
        if not tmdb_id or not str(tmdb_id).isdigit():
            return {}

        # initialise cache once
        if not hasattr(self, "tmdb_cache"):
            self.tmdb_cache = {}

        # return cached (including cached failures)
        if tmdb_id in self.tmdb_cache:
            return self.tmdb_cache[tmdb_id]

        # decide order to probe
        probe_order = []
        if media_hint == "movie":
            probe_order = ["movie"]
        elif media_hint == "tv":
            probe_order = ["tv"]
        else:
            probe_order = ["movie", "tv"]

        headers  = {"User-Agent": "Mozilla/5.0"}
        context  = ssl._create_unverified_context()
        patterns = {
            "desc":  re.compile(r'<div class="overview">\s*<p[^>]*>(.*?)</p>', re.DOTALL),
            "desc2": re.compile(r'<meta name="description" content="(.*?)"'),
            "title": re.compile(r'<title>(.*?)\s*\|\s*The Movie Database', re.DOTALL),
            "rating":re.compile(r'<span class="user_score_chart"[^>]+data-percent="(\d+)"'),
            "year":  re.compile(r'<span class="release">.*?(\d{4})</span>'),
        }

        for path in probe_order:
            url = f"https://www.themoviedb.org/{path}/{tmdb_id}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10, context=context) as resp:
                    html_data = resp.read().decode("utf-8")

                # --- scrape ---
                desc_match  = patterns["desc"].search(html_data) or patterns["desc2"].search(html_data)
                title_match = patterns["title"].search(html_data)
                rate_match  = patterns["rating"].search(html_data)
                year_match  = patterns["year"].search(html_data)

                result = {
                    "title":       title_match.group(1).strip()  if title_match else "",
                    "description": desc_match.group(1).strip()   if desc_match else "",
                    "rating":      f"{int(rate_match.group(1))/10:.1f}/10" if rate_match else "",
                    "year":        year_match.group(1)           if year_match else "",
                }
                # store & return
                self.tmdb_cache[tmdb_id] = result
                return result

            except urllib.error.HTTPError as http_err:
                if http_err.code == 404:
                    # try next path in order
                    continue
                else:
                    print("TMDb fetch error:", http_err)
                    break
            except Exception as e:
                print("TMDb fetch error:", e)
                break

        # cache the miss so we do not retry every hover
        self.tmdb_cache[tmdb_id] = {}
        return {}




    def _current_epg_description(self, entry):
        """
        Return the description of the programme that is *on-air now* for the
        supplied LIVE entry.  If none is airing, return the first upcoming
        programme’s description.  If the channel is not in the EPG, return ''.
        """
        try:
            if not self.epg_data:
                return ""

            # --- locate the EPG channel id -----------------------------------
            epg_id = (entry.get("epg_channel_id") or "").strip().lower()
            if not epg_id:
                # fall back to fuzzy name-map
                ch_name = normalize_channel_name(entry.get("name", ""))
                epg_id  = self.epg_name_map.get(ch_name, "")

            if not epg_id or epg_id not in self.epg_data:
                return ""

            now      = datetime.now(tz=tz.tzlocal())
            epg_list = self.epg_data[epg_id]

            # --- pick "current" (or very next) programme ---------------------
            current = None
            for p in epg_list:
                start = parser.parse(p["start_time"])
                stop  = parser.parse(p["stop_time"])
                if start <= now <= stop:
                    current = p
                    break
                if start > now and current is None:
                    current = p   # first upcoming show, just in case

            return (current or {}).get("description", "")

        except Exception as err:
            print("EPG helper error:", err)
            return ""



    def _lazy_load_movie_info(self, entry):
        if entry.get("_info_fetched"):
            return

        vod_id = entry.get("stream_id")
        if not vod_id:
            entry["_info_fetched"] = True
            return

        try:
            info = self.make_request(
                self.get_http_method(),
                f"{self.server}/player_api.php",
                {
                    "username": self.username,
                    "password": self.password,
                    "action":   "get_vod_info",
                    "vod_id":   vod_id
                },
                timeout=10
            ).json().get("info", {})

            entry["info"] = info
            entry["plot"]        = info.get("plot", "")
            entry["stream_icon"] = info.get("movie_image", entry.get("stream_icon", ""))
            entry["tmdb_id"]     = (info.get("tmdb_id") or info.get("imdb_id") or "")

        except Exception as err:
            print("Lazy VOD-info fetch failed:", err)

        entry["_info_fetched"] = True



    def _lazy_load_series_info(self, entry):
        if entry.get("_info_fetched"):
            return

        series_id = entry.get("series_id")
        episode_id = entry.get("id")

        try:
            # Fetch for series
            if series_id:
                info = self.make_request(
                    self.get_http_method(),
                    f"{self.server}/player_api.php",
                    {
                        "username": self.username,
                        "password": self.password,
                        "action":   "get_series_info",
                        "series_id": series_id
                    },
                    timeout=10
                ).json().get("info", {})
                entry["info"] = info
            # For episodes, info may be already present (most APIs send it inline)
            elif episode_id:
                if entry.get("info"):
                    entry["_info_fetched"] = True
                    return
                entry["info"] = {}
            else:
                entry["info"] = {}

        except Exception as err:
            print("Lazy Series/Episode-info fetch failed:", err)

        entry["_info_fetched"] = True




    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ToolTip:
            for widget, tab in [
                (self.channel_list_live,   "LIVE"),
                (self.channel_list_movies, "Movies"),
                (self.channel_list_series, "Series")
            ]:
                if obj is widget.viewport():
                    idx = widget.indexAt(event.pos())
                    if not idx.isValid():
                        break

                    entry = widget.item(idx.row()).data(Qt.UserRole)
                    if not isinstance(entry, dict):
                        return False

                    # ==== MOVIE TOOLTIP ====
                    if tab == "Movies":
                        if not entry.get("_info_fetched"):
                            self._lazy_load_movie_info(entry)
                        info = entry.get("info", {})
                        plot = info.get("plot", "") or entry.get("plot", "")
                        genre = info.get("genre", "")
                        rating = str(info.get("rating", ""))
                        release_date = info.get("releasedate") or info.get("releaseDate", "")
                        duration = info.get("duration", "")
                        cast = info.get("cast", "")
                        director = info.get("director", "")
                        trailer = info.get("youtube_trailer", "")
                        tmdb_id = info.get("tmdb_id", "") or entry.get("tmdb_id", "")

                        if not plot and tmdb_id:
                            plot = self.fetch_tmdb_description(tmdb_id).get("description", "")
                        if not plot:
                            plot = "No description available."

                        details = []
                        if genre: details.append(f"<b>Genre:</b> {html.escape(genre)}")
                        if rating: details.append(f"<b>Rating:</b> {html.escape(rating)}")
                        if release_date: details.append(f"<b>Release:</b> {html.escape(str(release_date))}")
                        if duration: details.append(f"<b>Duration:</b> {html.escape(duration)}")
                        if cast: details.append(f"<b>Cast:</b> {html.escape(cast)}")
                        if director: details.append(f"<b>Director:</b> {html.escape(director)}")
                        if trailer:
                            details.append(f'Trailer: https://youtu.be/{html.escape(trailer)}')

                        details_html = "<br>".join(details)
                        desc_html = html.escape(plot).replace("\n", "<br>")

                        icon_html = ""
                        poster_url = info.get("movie_image") or entry.get("stream_icon") or entry.get("cover", "")
                        local = self.get_cached_icon_path(poster_url)
                        if local:
                            icon_html = f'<img src="{local}" width="160"><br>'

                        movie_title = info.get("name", entry.get("name", "Untitled"))
                        tooltip = (
                            f'<div style="padding:0;margin:0;font-size:13px;max-width:400px;'
                            f'font-family:Arial;white-space:normal;word-wrap:break-word;">'
                            f'{icon_html}<b>{html.escape(movie_title)}</b><br>'
                            f'{details_html}<br><br>{desc_html}</div>'
                        )

                        QToolTip.showText(widget.mapToGlobal(event.pos()), tooltip)
                        return True

                    # ==== SERIES/EPISODE TOOLTIP ====
                    if tab == "Series":
                        if not entry.get("_info_fetched"):
                            self._lazy_load_series_info(entry)
                        info = entry.get("info", {})
                        

                        # Use both 'title' and 'name' in case one is missing
                        item_title = entry.get("title") or info.get("name") or entry.get("name", "Untitled")
                        plot = info.get("plot", "") or entry.get("plot", "")
                        genre = info.get("genre", "")
                        rating = str(info.get("rating", ""))
                        # Handle both 'releasedate' and 'releaseDate'
                        release_date = info.get("releasedate") or info.get("releaseDate", "")
                        duration = info.get("duration", "")
                        cast = info.get("cast", "")
                        director = info.get("director", "")
                        trailer = info.get("youtube_trailer", "")

                        details = []
                        if genre: details.append(f"<b>Genre:</b> {html.escape(genre)}")
                        if rating: details.append(f"<b>Rating:</b> {html.escape(rating)}")
                        if release_date: details.append(f"<b>Release:</b> {html.escape(str(release_date))}")
                        if duration: details.append(f"<b>Duration:</b> {html.escape(duration)}")
                        if cast: details.append(f"<b>Cast:</b> {html.escape(cast)}")
                        if director: details.append(f"<b>Director:</b> {html.escape(director)}")
                        if trailer:
                            details.append(f'Trailer: https://youtu.be/{html.escape(trailer)}')

                        details_html = "<br>".join(details)
                        desc_html = html.escape(plot).replace("\n", "<br>")

                        icon_html = ""
                        poster_url = info.get("movie_image") or entry.get("stream_icon") or entry.get("cover", "")
                        local = self.get_cached_icon_path(poster_url)
                        if local:
                            icon_html = f'<img src="{local}" width="160"><br>'

                        tooltip = (
                            f'<div style="padding:0;margin:0;font-size:13px;max-width:400px;'
                            f'font-family:Arial;white-space:normal;word-wrap:break-word;">'
                            f'{icon_html}<b>{html.escape(str(item_title))}</b><br>'
                            f'{details_html}<br><br>{desc_html}</div>'
                        )

                        QToolTip.showText(widget.mapToGlobal(event.pos()), tooltip)
                        return True

                    # ==== LIVE TOOLTIP (EPG) ====
                    if tab == "LIVE" and self.epg_data:
                        desc = self._current_epg_description(entry) or "No current EPG information available."
                        desc_html = html.escape(desc).replace("\n", "<br>")
                        title_html = html.escape(entry.get("name", "Untitled"))
                        tooltip = (
                            f'<div style="padding:0;margin:0;font-size:13px;max-width:380px;'
                            f'font-family:Arial;white-space:normal;word-wrap:break-word;">'
                            f'<b>{title_html}</b><br>{desc_html}</div>'
                        )
                        if desc.strip():
                            QToolTip.showText(widget.mapToGlobal(event.pos()), tooltip)
                        return True

        return super().eventFilter(obj, event)
















    def get_cached_icon_path(self, url):
        try:
            if not url:
                return ""

            os.makedirs(Path.home() / '.iptv' / 'icons', exist_ok=True)
            ext = os.path.splitext(url)[-1] if '.' in url else '.jpg'
            filename = re.sub(r'\W+', '_', url) + ext
            local_path = Path.home() / '.iptv' / 'icons' / filename

            if not local_path.exists():
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

                # 🔐 Disable SSL cert verification (safe for public image downloads)
                ssl_ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response, open(local_path, 'wb') as out_file:
                    out_file.write(response.read())

            return str(local_path)

        except Exception as e:
            print(f"Failed to cache icon: {e}")
            return ""



    def show_channels(self, list_widget, tab_name):
        """
        Populate the QListWidget for LIVE / Movies / Series.

        • LIVE:   – no tooltip at all when EPG is not available
                  – EPG description shown later by eventFilter once EPG is loaded
                  – no poster icon (per your last request)
        • Movies / Series: keep normal icons & placeholder tooltip
        """
        try:
            list_widget.clear()

            # ─── “Go Back” at sub-levels ─────────────────────────────────────────
            if self.navigation_stacks[tab_name]:
                back_item = QListWidgetItem("Go Back")
                back_item.setIcon(self.go_back_icon)
                list_widget.addItem(back_item)

            # choose an icon only for Movies / Series
            if tab_name == "LIVE":
                row_icon = QIcon()                # blank – we don’t want icons
            elif tab_name == "Movies":
                row_icon = self.movies_channel_icon
            elif tab_name == "Series":
                row_icon = self.series_channel_icon
            else:
                row_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

            items = []
            now = datetime.now(tz=tz.tzlocal()) if self.epg_data else None

            for entry in self.entries_per_tab[tab_name]:
                display_text = entry.get("name", "Unnamed")
                tooltip_text = ""                 # defaults to nothing

                # ─── LIVE: append on-air title to row text (if EPG ready) ───────
                if tab_name == "LIVE" and self.epg_data:
                    epg_id = entry.get("epg_channel_id") or ""
                    if not epg_id:
                        ch_norm = normalize_channel_name(entry.get("name", ""))
                        epg_id  = self.epg_name_map.get(ch_norm, "")
                    epg_list = self.epg_data.get(epg_id, [])

                    for prog in epg_list:
                        start = parser.parse(prog["start_time"])
                        stop  = parser.parse(prog["stop_time"])
                        if start <= now <= stop:
                            # add programme title & time window to the row text
                            start_s = start.astimezone(tz.tzlocal()).strftime("%I:%M %p")
                            stop_s  = stop.astimezone(tz.tzlocal()).strftime("%I:%M %p")
                            display_text += f" – {prog['title']} ({start_s}-{stop_s})"
                            tooltip_text   = prog["description"]          # may be “”
                            break

                # ─── Movies / Series placeholder (“Loading preview…”) ───────────
                elif tab_name in ("Movies", "Series"):
                    tooltip_text = "Loading preview…"

                # build list row --------------------------------------------------
                itm = QListWidgetItem(display_text)
                itm.setData(Qt.UserRole, entry)
                itm.setIcon(row_icon)

                # LIVE: show nothing until EPG is ready
                if tab_name == "LIVE" and not self.epg_data:
                    itm.setToolTip("")          # absolutely no hover text
                else:
                    itm.setToolTip(tooltip_text)

                items.append(itm)

            # alphabetical order
            items.sort(key=lambda x: x.text())
            for itm in items:
                list_widget.addItem(itm)

            list_widget.verticalScrollBar().setValue(0)
        except Exception as err:
            print("Error displaying channels:", err)





    def fetch_series_in_category(self, category_name):
        try:
            list_widget = self.get_list_widget('Series')
            curr_scroll = list_widget.verticalScrollBar().value()
            if self.navigation_stacks['Series']:
                self.navigation_stacks['Series'][-1]['scroll_position'] = curr_scroll
            else:
                self.top_level_scroll_positions['Series'] = curr_scroll

            category_id = next(g["category_id"]
                               for g in self.groups["Series"]
                               if g["category_name"] == category_name)

            params = {
                "username": self.username,
                "password": self.password,
                "action":   "get_series",
                "category_id": category_id
            }
            resp = self.make_request(self.get_http_method(),
                                     f"{self.server}/player_api.php",
                                     params)
            resp.raise_for_status()
            series_list = resp.json()

            # 🔑  store for quick lookup (poster / plot / tmdb_id, …)
            self.series_lookup = {s["series_id"]: s for s in series_list}

            self.navigation_stacks['Series'].append({
                "level": "series_categories",
                "data": {"series_list": series_list},
                "scroll_position": 0
            })
            self.show_series_in_category(series_list)

        except Exception as e:
            print("Error fetching series:", e)


    def show_series_in_category(self, series_list, restore_scroll_position=False, scroll_position=0):
        try:
            list_widget = self.channel_list_series

            list_widget.clear()
            if self.navigation_stacks['Series']:
                go_back_item = QListWidgetItem("Go Back")
                go_back_item.setIcon(self.go_back_icon)
                list_widget.addItem(go_back_item)

            items = []
            for entry in series_list:
                item = QListWidgetItem(entry["name"])
                item.setData(Qt.UserRole, entry)
                item.setIcon(self.series_channel_icon)
                items.append(item)

            items.sort(key=lambda x: x.text())
            for item in items:
                list_widget.addItem(item)

            if restore_scroll_position:
                QTimer.singleShot(0, lambda: list_widget.verticalScrollBar().setValue(scroll_position))
            else:
                list_widget.verticalScrollBar().setValue(0)

            self.current_series_list = series_list
        except Exception as e:
            print(f"Error displaying series: {e}")

    def fetch_seasons(self, series_entry):
        try:
            list_widget = self.get_list_widget('Series')
            current_scroll_position = list_widget.verticalScrollBar().value()
            stack = self.navigation_stacks['Series']
            if stack:
                stack[-1]['scroll_position'] = current_scroll_position

            http_method = self.get_http_method()
            params = {
                'username': self.username,
                'password': self.password,
                'action': 'get_series_info',
                'series_id': series_entry["series_id"]
            }

            episodes_url = f"{self.server}/player_api.php"
            response = self.make_request(http_method, episodes_url, params)
            response.raise_for_status()

            series_info = response.json()
            self.series_info = series_info

            seasons = list(series_info.get("episodes", {}).keys())
            self.navigation_stacks['Series'].append({'level': 'series', 'data': {'series_entry': series_entry, 'seasons': seasons}, 'scroll_position': 0})
            self.show_seasons(seasons)

        except Exception as e:
            print(f"Error fetching seasons: {e}")

    def show_seasons(self, seasons, restore_scroll_position=False, scroll_position=0):
        try:
            list_widget = self.channel_list_series
            list_widget.clear()
            if self.navigation_stacks['Series']:
                go_back_item = QListWidgetItem("Go Back")
                go_back_item.setIcon(self.go_back_icon)
                list_widget.addItem(go_back_item)

            seasons_int = sorted([int(season) for season in seasons])
            items = []
            for season in seasons_int:
                item = QListWidgetItem(f"Season {season}")
                item.setData(Qt.UserRole, str(season))
                item.setIcon(self.series_channel_icon)
                items.append(item)

            for item in items:
                list_widget.addItem(item)

            if restore_scroll_position:
                QTimer.singleShot(0, lambda: list_widget.verticalScrollBar().setValue(scroll_position))
            else:
                list_widget.verticalScrollBar().setValue(0)

            self.current_seasons = [str(season) for season in seasons_int]
        except Exception as e:
            print(f"Error displaying seasons: {e}")

    def fetch_episodes(self, series_entry, season_number):
        try:
            list_widget = self.get_list_widget('Series')
            current_scroll_position = list_widget.verticalScrollBar().value()
            stack = self.navigation_stacks['Series']
            if stack:
                stack[-1]['scroll_position'] = current_scroll_position

            episodes = self.series_info.get("episodes", {}).get(str(season_number), [])
            self.navigation_stacks['Series'].append({'level': 'season', 'data': {'season_number': season_number, 'episodes': episodes}, 'scroll_position': 0})
            self.show_episodes(episodes)

        except Exception as e:
            print(f"Error fetching episodes: {e}")

    def show_episodes(self, episodes, restore_scroll_position=False, scroll_position=0):
        try:
            lw = self.channel_list_series
            lw.clear()

            # ---- “Go Back” -----------------------------------------------------
            if self.navigation_stacks["Series"]:
                gb = QListWidgetItem("Go Back")
                gb.setIcon(self.go_back_icon)
                lw.addItem(gb)

            # ---- context -------------------------------------------------------
            series_entry   = self.navigation_stacks["Series"][-2]["data"]["series_entry"]
            series_title   = series_entry.get("name", "").strip()
            series_poster  = series_entry.get("cover") or series_entry.get("stream_icon") or ""
            series_tmdb_id = series_entry.get("tmdb_id")

            items = []
            for ep in sorted(episodes, key=lambda x: int(x.get("episode_num", 0))):
                

                # === Attach full info dict from API directly! ===
                ep_entry = dict(ep)  # start with a copy of the whole episode
                ep_info = ep.get("info", {})
                ep_entry["info"] = ep_info  # keep the full info dict

                # Compose display name as before
                season_no   = int(ep.get("season", 1))
                episode_no  = int(ep.get("episode_num", 1))
                code        = f"S{season_no:02d}E{episode_no:02d}"
                raw_title   = ep.get("title", "Untitled Episode").strip()
                clean_title = re.sub(re.escape(series_title), "", raw_title, flags=re.I).strip(" -")
                display_txt = f"{series_title} - {code} - {clean_title}"

                ep_entry["name"] = display_txt
                ep_entry["title"] = raw_title
                ep_entry["url"] = (
                    f"{self.server}/series/{self.username}/{self.password}/"
                    f"{ep['id']}.{ep.get('container_extension', 'm3u8')}"
                )
                ep_entry["plot"] = ep_info.get("plot", "")
                ep_entry["stream_icon"] = ep_info.get("movie_image", series_poster)
                ep_entry["tmdb_id"] = series_tmdb_id

                itm = QListWidgetItem(display_txt)
                itm.setData(Qt.UserRole, ep_entry)
                itm.setIcon(self.series_channel_icon)
                items.append(itm)

            for itm in items:
                lw.addItem(itm)

            # scroll restore
            if restore_scroll_position:
                QTimer.singleShot(0, lambda:
                    lw.verticalScrollBar().setValue(scroll_position))
            else:
                lw.verticalScrollBar().setValue(0)

            self.current_episodes = episodes

        except Exception as err:
            print("Error displaying episodes:", err)







    def play_channel(self, entry):
        try:
            stream_url = entry.get("url")
            if not stream_url:
                self.animate_progress(0, 100, "Stream URL not found")
                return

            if self.external_player_command:
                user_agent_argument = f":http-user-agent=AppleCoreMedia/1.0.0.20L563 (Apple TV; U; CPU OS 16_5 like Mac OS X; en_us)"
                command = [self.external_player_command, stream_url, user_agent_argument]

                if is_linux:
                    # Ensure the external player command is executable
                    if not os.access(self.external_player_command, os.X_OK):
                        self.animate_progress(0, 100, "Selected player is not executable")
                        return

                subprocess.Popen(command)
            else:
                self.animate_progress(0, 100, "No external player configured")
        except Exception as e:
            print(f"Error playing channel: {e}")
            self.animate_progress(0, 100, "Error playing channel")



    def on_tab_change(self, index):
        try:
            tab_name = self.tab_widget.tabText(index)

            if tab_name == "Info":
                if not self.info_tab_initialized:
                    self.result_display.clear()
                    self.result_display.setText("Ready to fetch and display data.")
                    self.info_tab_initialized = True
                return

            if self.login_type == 'xtream':
                stack = self.navigation_stacks.get(tab_name, [])
                list_widget = self.get_list_widget(tab_name)

                if not stack:
                    self.update_category_lists(tab_name)
                    list_widget.verticalScrollBar().setValue(
                        self.top_level_scroll_positions.get(tab_name, 0)
                    )
                else:
                    last_level = stack[-1]
                    level = last_level['level']
                    data = last_level['data']
                    scroll_position = last_level.get('scroll_position', 0)

                    if level == 'channels':
                        self.entries_per_tab[tab_name] = data['entries']
                        self.show_channels(list_widget, tab_name)
                        list_widget.verticalScrollBar().setValue(scroll_position)
                    elif level == 'series_categories':
                        self.show_series_in_category(
                            data['series_list'],
                            restore_scroll_position=True,
                            scroll_position=scroll_position
                        )
                    elif level == 'series':
                        self.show_seasons(
                            data['seasons'],
                            restore_scroll_position=True,
                            scroll_position=scroll_position
                        )
                    elif level == 'season':
                        self.show_episodes(
                            data['episodes'],
                            restore_scroll_position=True,
                            scroll_position=scroll_position
                        )

        except Exception as e:
            print(f"Error while switching tabs: {e}")

    def choose_external_player(self):
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setDirectory(QDir.home())  # Start in the user's home directory

            # Apply appropriate filters based on the OS
            if is_windows:
                file_dialog.setNameFilter("Executable files (*.exe *.bat)")
            elif is_mac:
                file_dialog.setNameFilter("Applications (*.app);;All files (*)")
            elif is_linux:
                file_dialog.setNameFilter("Executable files (*)")

            file_dialog.setWindowTitle("Select External Media Player")

            # Open the file dialog
            if file_dialog.exec_():
                file_paths = file_dialog.selectedFiles()
                if file_paths:
                    selected_path = file_paths[0]
                    
                    # Handle macOS .app bundles
                    if is_mac and selected_path.endswith(".app"):
                        # Extract the actual executable path from the .app bundle
                        executable_path = f"{selected_path}/Contents/MacOS/VLC"
                        if os.path.exists(executable_path):
                            self.external_player_command = executable_path
                        else:
                            print("Error: Executable not found inside .app bundle.")
                            return
                    else:
                        # Use the selected file path directly for other cases
                        self.external_player_command = selected_path

                    # Save the selected external player command
                    self.save_external_player_command()
                    print("External Player selected:", self.external_player_command)
            else:
                print("File dialog canceled.")
        except Exception as e:
            print("Error selecting external player:", str(e))




        





    def show_context_menu(self, position):
        sender = self.sender()
        menu = QMenu()
        sort_action = QAction("Sort Alphabetically", self)
        sort_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        sort_action.triggered.connect(lambda: self.sort_channel_list(sender))
        menu.addAction(sort_action)
        menu.exec_(sender.viewport().mapToGlobal(position))

    def sort_channel_list(self, list_widget):
        try:
            items = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.text() != "Go Back":
                    items.append(item)

            items.sort(key=lambda x: x.text())
            list_widget.clear()

            current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
            if self.navigation_stacks[current_tab]:
                go_back_item = QListWidgetItem("Go Back")
                go_back_item.setIcon(self.go_back_icon)
                list_widget.addItem(go_back_item)

            for item in items:
                list_widget.addItem(item)
        except Exception as e:
            print(f"Error sorting channel list: {e}")

    def search_in_list(self, tab_name, text):
        """
        When the user types in the search bar for the given tab (LIVE, Movies, Series):
          - If text is empty => revert to the original list in the current level
          - If at top-level => search category names
          - If inside a sub-level => search items in that sub-level (channels/movies/episodes)

        Displays "Not Found" if no results.
        """

        list_widget = self.get_list_widget(tab_name)
        if not list_widget:
            return

        # Trim leading/trailing spaces
        text = text.strip()

        # 1) If the search bar is cleared => revert to original view
        if not text:
            if self.navigation_stacks[tab_name]:
                # We are inside a sub-level
                last_level = self.navigation_stacks[tab_name][-1]
                level = last_level['level']
                data = last_level['data']
                scroll_position = last_level.get('scroll_position', 0)

                list_widget.clear()
                go_back_item = QListWidgetItem("Go Back")
                go_back_item.setIcon(self.go_back_icon)
                list_widget.addItem(go_back_item)

                if level == 'channels':
                    # Re-show the channels for this category
                    self.entries_per_tab[tab_name] = data['entries']
                    self.show_channels(list_widget, tab_name)
                    list_widget.verticalScrollBar().setValue(scroll_position)

                elif level == 'series_categories':
                    self.show_series_in_category(
                        data['series_list'],
                        restore_scroll_position=True,
                        scroll_position=scroll_position
                    )

                elif level == 'series':
                    self.show_seasons(
                        data['seasons'],
                        restore_scroll_position=True,
                        scroll_position=scroll_position
                    )

                elif level == 'season':
                    self.show_episodes(
                        data['episodes'],
                        restore_scroll_position=True,
                        scroll_position=scroll_position
                    )
            else:
                # No stack => top-level: show the categories again
                self.update_category_lists(tab_name)

            return  # Done reverting on empty text

        # 2) The user typed something => do the search
        list_widget.clear()

        # If inside a sub-level, we add "Go Back" at the top
        if self.navigation_stacks[tab_name]:
            go_back_item = QListWidgetItem("Go Back")
            go_back_item.setIcon(self.go_back_icon)
            list_widget.addItem(go_back_item)

        filtered_items = []

        # 2A) If we are at TOP-LEVEL (stack is empty):
        #     => Search among category names in self.groups[tab_name]
        if not self.navigation_stacks[tab_name]:
            group_list = self.groups.get(tab_name, [])
            for group in group_list:
                cat_name = group["category_name"]
                if text.lower() in cat_name.lower():
                    # We found a matching category
                    item = QListWidgetItem(cat_name)
                    if tab_name == 'LIVE':
                        item.setIcon(self.live_channel_icon)
                    elif tab_name == 'Movies':
                        item.setIcon(self.movies_channel_icon)
                    elif tab_name == 'Series':
                        item.setIcon(self.series_channel_icon)
                    else:
                        item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))

                    filtered_items.append(item)

        # 2B) If we are INSIDE a sub-level (stack is not empty):
        else:
            # Look at the last level
            last_level = self.navigation_stacks[tab_name][-1]
            level = last_level['level']

            if level == 'channels':
                # We’re in a channel list => search channels in entries_per_tab[tab_name]
                for entry in self.entries_per_tab[tab_name]:
                    channel_name = entry.get('name', '')
                    if text.lower() in channel_name.lower():
                        item = QListWidgetItem(channel_name)
                        item.setData(Qt.UserRole, entry)
                        if tab_name == 'LIVE':
                            item.setIcon(self.live_channel_icon)
                        elif tab_name == 'Movies':
                            item.setIcon(self.movies_channel_icon)
                        else:
                            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
                        filtered_items.append(item)

            elif level == 'series_categories':
                # We’re in a series-list => search in self.current_series_list
                for series_info in self.current_series_list:
                    series_name = series_info["name"]
                    if text.lower() in series_name.lower():
                        item = QListWidgetItem(series_name)
                        item.setData(Qt.UserRole, series_info)
                        item.setIcon(self.series_channel_icon)
                        filtered_items.append(item)

            elif level == 'series':
                # We’re listing the seasons => let's see if user typed "Season 1", "Season 2", etc.
                for season in self.current_seasons:
                    label = f"Season {season}"
                    if text.lower() in label.lower():
                        item = QListWidgetItem(label)
                        item.setData(Qt.UserRole, season)
                        item.setIcon(self.series_channel_icon)
                        filtered_items.append(item)

            elif level == 'season':
                # We’re listing episodes => search by episode title
                for episode in self.current_episodes:
                    ep_title = episode.get('title', '')
                    if text.lower() in ep_title.lower():
                        display_text = f"Episode {episode['episode_num']}: {ep_title}"
                        episode_entry = {
                            "season": episode.get('season'),
                            "episode_num": episode['episode_num'],
                            "name": display_text,
                            "url": f"{self.server}/series/{self.username}/{self.password}/{episode['id']}.{episode.get('container_extension', 'm3u8')}",
                            "title": ep_title
                        }
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, episode_entry)
                        item.setIcon(self.series_channel_icon)
                        filtered_items.append(item)

        # 3) After building 'filtered_items', decide what to show
        if not filtered_items:
            # No results => show "Not Found"
            not_found_item = QListWidgetItem("Not Found")
            not_found_item.setFlags(not_found_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            list_widget.addItem(not_found_item)
        else:
            # Sort them by text if you like
            filtered_items.sort(key=lambda x: x.text().lower())
            for item in filtered_items:
                list_widget.addItem(item)


    def get_list_widget(self, tab_name):
        return self.list_widgets.get(tab_name)

    def load_external_player_command(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'ExternalPlayer' in config:
            self.external_player_command = config['ExternalPlayer'].get('Command', '')

    def save_external_player_command(self):
        config = configparser.ConfigParser()
        config['ExternalPlayer'] = {'Command': self.external_player_command}
        with open('config.ini', 'w') as config_file:
            config.write(config_file)

    def on_epg_checkbox_toggled(self, state):
        # If EPG is checked after we already logged in and no EPG data loaded, start it now.
        if state == Qt.Checked:
            if self.login_type == 'xtream' and self.server and self.username and self.password and not self.epg_data:
                # Reset progress and load EPG
                self.reset_progress_bar()
                self.animate_progress(0, 50, "Loading EPG data...")
                self.load_epg_data_async()

    def open_address_book(self):
        dialog = AddressBookDialog(self)
        dialog.exec_()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    player = IPTVPlayerApp()
    player.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
