import os
import json

from .config import RAM_SIZE, JVM_ARGS, MINECRAFT_FOLDER

class Settings:
    def __init__(self):
        self._settings_file = os.path.join(MINECRAFT_FOLDER, "settings.json")
        self._minecraft_options = os.path.join(MINECRAFT_FOLDER, "options.txt")
        # Game settings
        self.window_width = 854
        self.window_height = 480
        self.fullscreen = False
        self.minimize_launcher = True
        self.close_launcher = False
        self.min_use_ram = max(RAM_SIZE // 2, 6 * 1024)
        self.max_use_ram = self.min_use_ram
        self.java_args = JVM_ARGS

    def load(self):
        if os.path.exists(self._settings_file):
            with open(self._settings_file, "r") as f:
                data = json.load(f)
                self.window_width = data.get("window_width", self.window_width)
                self.window_height = data.get("window_height", self.window_height)
                self.fullscreen = data.get("fullscreen", self.fullscreen)
                self.minimize_launcher = data.get("minimize_launcher", self.minimize_launcher)
                self.close_launcher = data.get("close_launcher", self.close_launcher)
                self.min_use_ram = data.get("min_use_ram", self.min_use_ram)
                self.max_use_ram = data.get("max_use_ram", self.max_use_ram)
                self.java_args = data.get("java_args", self.java_args)
        else:
            self.save()
                
    def save(self):
        data = {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "fullscreen": self.fullscreen,
            "minimize_launcher": self.minimize_launcher,
            "close_launcher": self.close_launcher,
            "min_use_ram": self.min_use_ram,
            "max_use_ram": self.max_use_ram,
            "java_args": self.java_args
        }
        with open(self._settings_file, "w") as f:
            json.dump(data, f)
            

settings = Settings()
settings.load()
