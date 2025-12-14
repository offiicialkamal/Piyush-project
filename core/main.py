import json
import threading
from file_handlers import read_json


class commenter(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        print("started threed")
