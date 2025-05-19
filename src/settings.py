import os
import json

from config import RAM_SIZE, JVM_ARGS, APPDATA_FOLDER


class Settings:
    def __init__(self):
        self._settings_file = os.path.join(APPDATA_FOLDER, "settings.json")
        self._minecraft_options = None
        # Game settings
        self._minecraft_directory = APPDATA_FOLDER / ".minecraft"
        self.window_width = 854
        self.window_height = 480
        self.fullscreen = False
        self.minimize_launcher = True
        self.close_launcher = False
        self.min_use_ram = min(RAM_SIZE // 2, 6 * 1024)
        self.max_use_ram = self.min_use_ram
        self.java_args = JVM_ARGS

    def load(self):
        if os.path.exists(self._settings_file):
            with open(self._settings_file, "r") as f:
                data = json.load(f)
                self._minecraft_directory = data.get(
                    "minecraft_directory", self._minecraft_directory
                )
                if not os.path.exists(self._minecraft_directory):
                    # Create the directory if it doesn't exist
                    os.makedirs(self._minecraft_directory)
                self._minecraft_options = os.path.join(
                    self._minecraft_directory, "options.txt"
                )
                if not os.path.exists(self._minecraft_options):
                    # Create the file if it doesn't exist
                    with open(self._minecraft_options, "w") as f:
                        f.write("fullscreen:false\n")
                else:
                    self._set_fullscreen()
                self._minecraft_directory = os.path.abspath(self._minecraft_directory)
                self.window_width = data.get("window_width", self.window_width)
                self.window_height = data.get("window_height", self.window_height)
                self.fullscreen = data.get("fullscreen", self.fullscreen)
                self.minimize_launcher = data.get(
                    "minimize_launcher", self.minimize_launcher
                )
                self.close_launcher = data.get("close_launcher", self.close_launcher)
                self.min_use_ram = data.get("min_use_ram", self.min_use_ram)
                self.max_use_ram = data.get("max_use_ram", self.max_use_ram)
                self.java_args = data.get("java_args", self.java_args)
        else:
            self.save()
        # create minecraft directory symlink to the appdata folder
        self.link_minecraft_directory()

    def save(self):
        data = {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "fullscreen": self.fullscreen,
            "minimize_launcher": self.minimize_launcher,
            "close_launcher": self.close_launcher,
            "min_use_ram": self.min_use_ram,
            "max_use_ram": self.max_use_ram,
            "java_args": self.java_args,
            "minecraft_directory": str(self._minecraft_directory),
        }
        with open(self._settings_file, "w") as f:
            json.dump(data, f)

        if not os.path.exists(self._minecraft_directory):
            # Create the directory if it doesn't exist
            os.makedirs(self._minecraft_directory)
        self._minecraft_options = os.path.join(self._minecraft_directory, "options.txt")
        if not os.path.exists(self._minecraft_options):
            # Create the file if it doesn't exist
            with open(self._minecraft_options, "w") as f:
                f.write("fullscreen:false\n")
        self._set_fullscreen()
        # create minecraft directory symlink to the appdata folder
        self.link_minecraft_directory()

    def link_minecraft_directory(self):
        # remove old symlink if exists
        if os.path.islink(APPDATA_FOLDER / "minecraft"):
            os.remove(APPDATA_FOLDER / "minecraft")
        # create new symlink
        os.symlink(
            os.path.abspath(self._minecraft_directory),
            os.path.abspath(APPDATA_FOLDER / "minecraft"),
        )

    def _set_fullscreen(self):
        # Set the Minecraft options to fullscreen
        if not os.path.exists(self._minecraft_options):
            # Create the file with the fullscreen option if it doesn't exist
            with open(self._minecraft_options, "w") as f:
                f.write(f"fullscreen:{str(self.fullscreen).lower()}\n")
            return

        with open(self._minecraft_options, "r") as f:
            lines = f.readlines()

        with open(self._minecraft_options, "w") as f:
            for line in lines:
                if line.startswith("fullscreen:"):
                    f.write(f"fullscreen:{str(self.fullscreen).lower()}\n")


settings = Settings()
settings.load()
