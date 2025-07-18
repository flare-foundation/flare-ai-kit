import requests

class Goldsky:
    def __init__(self, api_key: str, base_url: str = "https://api.goldsky.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_blocks(self, params=None):
        url = f"{self.base_url}/v1/blocks"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_logs(self, params=None):
        url = f"{self.base_url}/v1/logs"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_traces(self, params=None):
        url = f"{self.base_url}/v1/traces"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def query_events(self, event_type: str, params=None):
        url = f"{self.base_url}/v1/events/{event_type}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json() 