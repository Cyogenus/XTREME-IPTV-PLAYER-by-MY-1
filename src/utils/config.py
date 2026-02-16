import configparser
import os

class ConfigManager:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['Theme'] = {'Dark': 'False'}
            self.config['General'] = {'ExternalPlayer': ''}
            self.save()

    def save(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def get_theme(self):
        return self.config.getboolean('Theme', 'Dark', fallback=False)

    def set_theme(self, dark):
        if 'Theme' not in self.config:
            self.config['Theme'] = {}
        self.config['Theme']['Dark'] = str(dark)
        self.save()

    def get_external_player(self):
        return self.config.get('General', 'ExternalPlayer', fallback='')

    def set_external_player(self, path):
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General']['ExternalPlayer'] = path
        self.save()
