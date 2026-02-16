import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt

from src.api.xtream_api import XtreamAPI, CUSTOM_USER_AGENT
from src.api.m3u_parser import M3UParser
from src.ui.dashboard import DashboardView
from src.ui.login_view import LoginView
from src.ui.content_views import ContentListView
from src.ui.details_view import DetailsView
from src.ui.internal_player import InternalPlayer
from src.utils.config import ConfigManager
from src.utils.worker import GenericWorker
from src.utils.epg_worker import EPGWorker
from src.db.db_manager import DatabaseManager
from PyQt5.QtCore import Qt, QThreadPool

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XTREME IPTV PLAYER PRO")
        self.resize(1280, 720)
        
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.xtream_api = XtreamAPI()
        self.m3u_parser = M3UParser()
        
        self.categories = {}
        self.current_tab = None
        self.navigation_state = {} 
        
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)
        
        # Views
        # Lazy Views (Initialized on demand)
        self.live_view = None
        self.movies_view = None
        self.series_view = None
        
        self.login_view = LoginView()
        self.dashboard_view = DashboardView()
        self.details_view = DetailsView()
        self.internal_player = InternalPlayer()
        
        self.central_stack.addWidget(self.login_view)
        self.central_stack.addWidget(self.dashboard_view)
        self.central_stack.addWidget(self.details_view)
        self.central_stack.addWidget(self.internal_player)
        
        # Signals
        self.login_view.login_xtream.connect(self.handle_xtream_login)
        self.login_view.login_m3u.connect(self.handle_m3u_login)
        self.login_view.profile_selected.connect(self.handle_profile_login)
        self.login_view.delete_profile_requested.connect(self.handle_delete_profile)
        
        self.dashboard_view.tile_clicked.connect(self.handle_tile_click)
        
        self.details_view.play_clicked.connect(self.play_stream)
        self.details_view.back_clicked.connect(self.handle_back)
        self.internal_player.back_clicked.connect(self.handle_back)
        
        # We'll connect category/item signals in lazy init

        # Initial Profile Load
        self.refresh_profiles()

    def apply_style(self):
        # Base style to achieve that modern look
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e293b);
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 8px;
                color: white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
        """)

    def refresh_profiles(self):
        profiles = self.db.get_profiles()
        self.login_view.set_profiles(profiles)

    def handle_delete_profile(self, profile_id):
        self.db.delete_profile(profile_id)
        self.refresh_profiles()

    def handle_profile_login(self, profile):
        login_type = profile.get('login_type')
        if login_type == 'xtream':
            self.handle_xtream_login(profile['name'], profile['server'], profile['username'], profile['password'], save=False)
        else:
            self.handle_m3u_login(profile['name'], profile['server'], save=False)

    def handle_xtream_login(self, name, server, user, password, save=True):
        self.xtream_api.set_credentials(server, user, password)
        
        # Show some status
        self.statusBar().showMessage("Logging in and fetching categories...")
        self.login_view.setEnabled(False)
        
        worker = GenericWorker(self.xtream_api.fetch_categories)
        worker.signals.finished.connect(lambda cats: self.on_categories_loaded(cats, name, server, user, password, save))
        worker.signals.error.connect(self.on_api_error)
        QThreadPool.globalInstance().start(worker)

    def on_categories_loaded(self, categories, name, server, user, password, save):
        self.login_view.setEnabled(True)
        self.statusBar().clearMessage()
        
        self.categories = categories
        if any(self.categories.values()):
            if save:
                self.db.add_profile(name, server, user, password, 'xtream')
                self.refresh_profiles()
            
            # Fetch account info in background too
            info_worker = GenericWorker(self.xtream_api.fetch_account_info)
            info_worker.signals.finished.connect(self.on_account_info_loaded)
            QThreadPool.globalInstance().start(info_worker)
            
            self.central_stack.setCurrentWidget(self.dashboard_view)
        else:
            QMessageBox.critical(self, "Error", "Failed to login. Check your credentials or server status.")

    def on_account_info_loaded(self, info):
        user_info = info.get("user_info", {})
        self.dashboard_view.update_user_info(
            user_info.get("username", self.xtream_api.username), 
            user_info.get("exp_date", "Unlimited")
        )

    def on_api_error(self, err_msg):
        self.login_view.setEnabled(True)
        self.statusBar().clearMessage()
        print(f"API Thread Error: {err_msg}")
        QMessageBox.critical(self, "Network Error", "An error occurred during communication with the server.")

    def handle_m3u_login(self, name, url, save=True):
        if self.m3u_parser.parse_url(url):
            if save:
                self.db.add_profile(name, url, "", "", 'm3u')
                self.refresh_profiles()
                
            self.categories = self.m3u_parser.categories
            self.dashboard_view.update_user_info(name, "N/A")
            self.central_stack.setCurrentWidget(self.dashboard_view)
        else:
            QMessageBox.critical(self, "Error", "Failed to load M3U playlist.")

    def handle_tile_click(self, tile_type):
        if tile_type == "Settings":
             # TODO: implement settings
             return
        
        self.current_tab = tile_type
        view_map = {"LIVE": self.live_view, "Movies": self.movies_view, "Series": self.series_view}
        view = view_map.get(tile_type)
        
        if not view:
            # Lazy Init
            if tile_type == "LIVE":
                self.live_view = ContentListView("LIVE")
                view = self.live_view
            elif tile_type == "Movies":
                self.movies_view = ContentListView("Movies")
                view = self.movies_view
            elif tile_type == "Series":
                self.series_view = ContentListView("Series")
                view = self.series_view
            
            if view:
                self.central_stack.addWidget(view)
                view.back_clicked.connect(self.handle_back)
                view.category_clicked.connect(lambda data, t=tile_type: self.handle_cat_click(t, data))
                view.item_clicked.connect(lambda data, t=tile_type: self.handle_item_click(t, data))

        self.central_stack.setCurrentWidget(view)
        
        # Determine mapping for M3U if necessary
        xtream_key = {"LIVE": "LIVE", "Movies": "Movies", "Series": "Series"}.get(tile_type)
        cat_list = self.categories.get(xtream_key, [])
        
        view.set_categories(cat_list)
        self.navigation_state[tile_type] = 'categories'

    def handle_cat_click(self, tab, data):
        cat_id = data.get('category_id')
        if not cat_id: return
        
        # Aggressive Cleanup
        from src.ui.delegates import ImageCache, IMAGE_POOL
        ImageCache.clear()
        
        # We can't cancel already running threads easily, 
        # but we can prevent new ones and clear the UI.
        self.statusBar().showMessage(f"Loading {tab}...")
        
        xtream_tab = {"LIVE": "LIVE", "Movies": "Movies", "Series": "Series"}.get(tab)
        
        if self.xtream_api.server: # Xtream mode
            worker = GenericWorker(self.xtream_api.fetch_streams, xtream_tab, cat_id)
            worker.signals.finished.connect(lambda streams: self.on_streams_loaded(tab, streams))
            worker.signals.error.connect(self.on_api_error)
            QThreadPool.globalInstance().start(worker)
        else: # M3U mode
            streams = self.m3u_parser.get_streams_in_category(cat_id)
            self.on_streams_loaded(tab, streams)

    def on_streams_loaded(self, tab, streams):
        self.statusBar().clearMessage()
        view_map = {"LIVE": self.live_view, "Movies": self.movies_view, "Series": self.series_view}
        view = view_map.get(tab)
        if view:
            view.set_items(streams)
            self.navigation_state[tab] = 'streams'

    def handle_item_click(self, tab, data):
        if tab == "LIVE":
            self.play_stream(data)
        elif tab == "Movies":
            self.statusBar().showMessage("Fetching movie details...")
            worker = GenericWorker(self.xtream_api.get_movie_info, data.get('stream_id'))
            worker.signals.finished.connect(self.on_movie_info_loaded)
            worker.signals.error.connect(self.on_api_error)
            QThreadPool.globalInstance().start(worker)
            self.navigation_state[tab] = 'details'
        elif tab == "Series":
            self.statusBar().showMessage("Fetching series details...")
            worker = GenericWorker(self.xtream_api.get_series_info, data.get('series_id'))
            worker.signals.finished.connect(self.on_series_info_loaded)
            worker.signals.error.connect(self.on_api_error)
            QThreadPool.globalInstance().start(worker)
            self.navigation_state[tab] = 'details'

    def on_movie_info_loaded(self, info):
        self.statusBar().clearMessage()
        self.details_view.set_movie_data(info)
        self.central_stack.setCurrentWidget(self.details_view)

    def on_series_info_loaded(self, info):
        self.statusBar().clearMessage()
        self.details_view.set_series_data(info)
        self.central_stack.setCurrentWidget(self.details_view)

    def handle_back(self):
        tab = self.current_tab
        state = self.navigation_state.get(tab)
        
        if state == 'player':
             self.internal_player.stop()
             # Return to previous view
             self.central_stack.setCurrentWidget(self.details_view if tab in ['Movies', 'Series'] else self.live_view)
             self.navigation_state[tab] = 'details' if tab in ['Movies', 'Series'] else 'streams'
        elif state == 'details':
            # Go back to streams grid
            view_map = {"LIVE": self.live_view, "Movies": self.movies_view, "Series": self.series_view}
            self.central_stack.setCurrentWidget(view_map[tab])
            self.navigation_state[tab] = 'streams'
        elif state == 'streams':
            # Go back to categories
            self.handle_tile_click(tab)
        else:
            # Go back to dashboard
            self.central_stack.setCurrentWidget(self.dashboard_view)

    def play_stream(self, data):
        url = data.get('url')
        if url:
             self.central_stack.setCurrentWidget(self.internal_player)
             self.navigation_state[self.current_tab or 'LIVE'] = 'player'
             self.internal_player.play(url)
    def closeEvent(self, event):
        QThreadPool.globalInstance().waitForDone()
        event.accept()
