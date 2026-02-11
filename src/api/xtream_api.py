import requests
import json
import re
from datetime import datetime

CUSTOM_USER_AGENT = (
    "Connection: Keep-Alive User-Agent: okhttp/5.0.0-alpha.2 "
    "Accept-Encoding: gzip, deflate"
)

class XtreamAPI:
    def __init__(self, server=None, username=None, password=None):
        self.server = self._fix_url(server) if server else None
        self.username = username
        self.password = password
        self.user_info = {}
        self.server_info = {}

    def _fix_url(self, url):
        if not url: return None
        url = url.strip().rstrip('/')
        if not url.startswith(('http://', 'https://')):
            url = f"http://{url}"
        return url

    def set_credentials(self, server, username, password):
        self.server = self._fix_url(server)
        self.username = username
        self.password = password

    def make_request(self, method, action, params=None, timeout=10):
        if not self.server: return None
        url = f"{self.server}/player_api.php"
        headers = {'User-Agent': CUSTOM_USER_AGENT}
        
        request_params = {
            'username': self.username,
            'password': self.password,
            'action': action
        }
        if params:
            request_params.update(params)

        try:
            if method == 'POST':
                return requests.post(url, data=request_params, headers=headers, timeout=timeout)
            else:
                return requests.get(url, params=request_params, headers=headers, timeout=timeout)
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def fetch_categories(self, http_method='GET'):
        categories = {
            "LIVE": [],
            "Movies": [],
            "Series": [],
        }
        try:
            res_live = self.make_request(http_method, 'get_live_categories')
            if res_live and res_live.status_code == 200:
                data = res_live.json()
                categories["LIVE"] = [{"category_id": c.get("category_id"), "category_name": c.get("category_name")} for c in data]

            res_vod = self.make_request(http_method, 'get_vod_categories')
            if res_vod and res_vod.status_code == 200:
                data = res_vod.json()
                categories["Movies"] = [{"category_id": c.get("category_id"), "category_name": c.get("category_name")} for c in data]

            res_series = self.make_request(http_method, 'get_series_categories')
            if res_series and res_series.status_code == 200:
                data = res_series.json()
                categories["Series"] = [{"category_id": c.get("category_id"), "category_name": c.get("category_name")} for c in data]
        except Exception as e:
            print(f"Error fetching categories: {e}")
        
        return categories

    def fetch_streams(self, tab_name, category_id, http_method='GET'):
        action = {
            "LIVE": "get_live_streams",
            "Movies": "get_vod_streams",
            "Series": "get_series"
        }.get(tab_name)
        
        if not action:
            return []

        try:
            params = {"category_id": category_id}
            response = self.make_request(http_method, action, params)
            if not response: return []
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                return []

            stream_type = {
                "LIVE": "live",
                "Movies": "movie",
                "Series": "series"
            }.get(tab_name)

            # Essential keys to keep
            essential_keys = {
                "name", "num", "stream_id", "series_id", "stream_icon", 
                "movie_image", "movie_icon", "cover", "series_cover", 
                "icon", "poster", "category_id", "rating", "rating_5based",
                "epg_channel_id", "url"
            }

            pruned_data = []
            for entry in data:
                sid = entry.get("stream_id") or entry.get("series_id")
                if sid:
                    if tab_name == "LIVE":
                        ext = "ts"
                    elif tab_name == "Movies":
                        ext = entry.get("container_extension", "mp4")
                    else:
                        ext = "" # Series don't have direct link here
                    
                    if ext:
                        entry["url"] = f"{self.server}/{stream_type}/{self.username}/{self.password}/{sid}.{ext}"
                
                epg_id = (entry.get("epg_channel_id") or "").strip().lower()
                entry["epg_channel_id"] = epg_id if epg_id else None
                
                # Prune and Cap to 5,000 items for memory stability
                pruned_entry = {k: entry[k] for k in essential_keys if k in entry}
                pruned_data.append(pruned_entry)
                
                if len(pruned_data) >= 5000:
                    break
            
            return pruned_data
        except Exception as e:
            print(f"Error fetching streams: {e}")
            return []

    def get_movie_info(self, movie_id, http_method='GET'):
        try:
            response = self.make_request(http_method, "get_vod_info", {"vod_id": movie_id})
            if not response: return {}
            data = response.json()
            
            # Construct URL for playback
            movie_data = data.get('movie_data', {})
            stream_id = movie_data.get('stream_id')
            ext = movie_data.get('container_extension', 'mp4')
            if stream_id:
                data['url'] = f"{self.server}/movie/{self.username}/{self.password}/{stream_id}.{ext}"
            
            return data
        except Exception as e:
            print(f"Error fetching movie info: {e}")
            return {}

    def get_series_info(self, series_id, http_method='GET'):
        try:
            response = self.make_request(http_method, "get_series_info", {"series_id": series_id})
            if not response: return {}
            data = response.json()
            
            # Construct URLs for episodes
            episodes = data.get('episodes', {})
            for season in episodes.values():
                for ep in season:
                    sid = ep.get('id')
                    ext = ep.get('container_extension', 'mp4')
                    if sid:
                        ep['url'] = f"{self.server}/series/{self.username}/{self.password}/{sid}.{ext}"
            
            return data
        except Exception as e:
            print(f"Error fetching series info: {e}")
            return {}

    def fetch_account_info(self):
        try:
            response = self.make_request('POST', '') # No action for panel data
            if not response: return {}
            response.raise_for_status()
            data = response.json()
            self.user_info = data.get("user_info", {})
            self.server_info = data.get("server_info", {})
            return data
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}
