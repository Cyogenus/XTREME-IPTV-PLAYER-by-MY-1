import re
import requests

class M3UParser:
    def __init__(self, url=None):
        self.url = url
        self.streams = []
        self.categories = {"LIVE": [], "Movies": [], "Series": []}

    def parse_url(self, url):
        self.url = url
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return self.parse_content(response.text)
        except Exception as e:
            print(f"Error fetching M3U: {e}")
            return False

    def parse_content(self, content):
        self.streams = []
        lines = content.splitlines()
        current_stream = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                current_stream = {}
                # Extract tags
                # Example: #EXTINF:-1 tvg-id="CNN.us" tvg-logo="http://..." group-title="News",CNN
                tags = re.findall(r'(\S+)="(.*?)"', line)
                for tag, value in tags:
                    if tag == 'tvg-id': current_stream['epg_channel_id'] = value
                    if tag == 'tvg-logo': current_stream['stream_icon'] = value
                    if tag == 'group-title': current_stream['category_name'] = value
                
                # Extract name
                name_match = re.search(r',(.*)$', line)
                if name_match:
                    current_stream['name'] = name_match.group(1).strip()
            
            elif line.startswith("http") or line:
                if not line.startswith("#"):
                    if current_stream.get('name'):
                        current_stream['url'] = line
                        # Guess category if not present
                        if not current_stream.get('category_name'):
                            current_stream['category_name'] = "Uncategorized"
                        
                        self.streams.append(current_stream)
                        current_stream = {}
        
        self._organize_categories()
        return True

    def _organize_categories(self):
        cat_map = {}
        for stream in self.streams:
            cat_name = stream.get('category_name', 'Uncategorized')
            if cat_name not in cat_map:
                cat_map[cat_name] = []
            cat_map[cat_name].append(stream)
        
        # Simple heuristic for M3U: everything is mostly LIVE unless specified
        # In a real app we might look for "VOD" or "Movies" in group titles
        self.categories["LIVE"] = [{"category_id": name, "category_name": name} for name in cat_map.keys()]
        # We store the actual streams in a way the UI can access
        self.grouped_streams = cat_map

    def get_streams_in_category(self, category_id):
        return self.grouped_streams.get(category_id, [])
