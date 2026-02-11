import requests
import xml.etree.ElementTree as ET
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject
from pathlib import Path
import os

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

    def run(self):
        try:
            params = {
                'username': self.username,
                'password': self.password,
                'action': 'get_short_epg' # or 'xmltv.php'
            }
            url = f"{self.server}/xmltv.php"
            headers = {'User-Agent': "Connection: Keep-Alive User-Agent: okhttp/5.0.0-alpha.2"}
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            epg_data, channel_id_to_names = self.parse_epg_data(response.content)
            self.signals.finished.emit(epg_data, channel_id_to_names)
        except Exception as e:
            self.signals.error.emit(str(e))

    def parse_epg_data(self, epg_xml_data):
        epg_data = {}
        channel_id_to_names = {}
        try:
            root = ET.fromstring(epg_xml_data)
            for channel in root.findall('channel'):
                channel_id = channel.get('id')
                names = [n.text for n in channel.findall('display-name')]
                channel_id_to_names[channel_id] = names

            for programme in root.findall('programme'):
                channel_id = programme.get('channel')
                start = programme.get('start')
                stop = programme.get('stop')
                title = programme.find('title').text if programme.find('title') is not None else ""
                desc = programme.find('desc').text if programme.find('desc') is not None else ""
                
                if channel_id not in epg_data:
                    epg_data[channel_id] = []
                epg_data[channel_id].append({
                    'start': start,
                    'stop': stop,
                    'title': title,
                    'desc': desc
                })
        except Exception as e:
            print(f"EPG Parse Error: {e}")
        return epg_data, channel_id_to_names
