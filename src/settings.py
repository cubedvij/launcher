import os
import json

from config import RAM_SIZE, JVM_ARGS, APPDATA_FOLDER


class Settings:
    def __init__(self):
        self._settings_file = os.path.join(APPDATA_FOLDER, "settings.json")
        # Game settings
        self.minecraft_directory = APPDATA_FOLDER / ".minecraft"
        self.minecraft_options = os.path.join(self.minecraft_directory, "options.txt")
        self.launcher_theme = "system"
        self.launcher_color = "deeppurple"
        self.launcher_border_radius = 8
        self.launcher_border_shape = "roundedRectangle"
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

                launcher_data = data.get("launcher", {})
                minecraft_data = data.get("minecraft", {})

                self.launcher_theme = launcher_data.get("theme", self.launcher_theme)
                self.launcher_color = launcher_data.get("color", self.launcher_color)
                self.launcher_border_radius = int(
                    launcher_data.get("border_radius", self.launcher_border_radius)
                )
                self.launcher_border_shape = launcher_data.get(
                    "border_shape", self.launcher_border_shape
                )

                self.window_width = launcher_data.get("window_width", self.window_width)
                self.window_height = launcher_data.get(
                    "window_height", self.window_height
                )
                self.minimize_launcher = launcher_data.get(
                    "minimize", self.minimize_launcher
                )
                self.close_launcher = launcher_data.get("close", self.close_launcher)
                self.java_args = launcher_data.get("java_args", self.java_args)

                self.fullscreen = minecraft_data.get("fullscreen", self.fullscreen)
                self.min_use_ram = minecraft_data.get("min_use_ram", self.min_use_ram)
                self.max_use_ram = minecraft_data.get("max_use_ram", self.max_use_ram)
                self.minecraft_directory = minecraft_data.get(
                    "directory", str(self.minecraft_directory)
                )
                self.minecraft_directory = os.path.abspath(self.minecraft_directory)
                self.minecraft_options = os.path.join(
                    self.minecraft_directory, "options.txt"
                )

                if not os.path.exists(self.minecraft_directory):
                    os.makedirs(self.minecraft_directory)
                if not os.path.exists(self.minecraft_options):
                    with open(self.minecraft_options, "w") as f:
                        f.write("fullscreen:false\n")
                self._set_fullscreen()
        else:
            self.save()

    def save(self):
        launcher_data = {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "theme": self.launcher_theme,
            "color": self.launcher_color,
            "border_radius": int(self.launcher_border_radius),
            "border_shape": self.launcher_border_shape,
            "minimize": self.minimize_launcher,
            "close": self.close_launcher,
            "java_args": self.java_args,
        }

        minecraft_data = {
            "fullscreen": self.fullscreen,
            "min_use_ram": self.min_use_ram,
            "max_use_ram": self.max_use_ram,
            "directory": str(self.minecraft_directory),
        }

        data = {
            "launcher": launcher_data,
            "minecraft": minecraft_data,
        }
        with open(self._settings_file, "w") as f:
            json.dump(data, f, indent=4)

        if not os.path.exists(self.minecraft_directory):
            # Create the directory if it doesn't exist
            os.makedirs(self.minecraft_directory)
        self.minecraft_options = os.path.join(self.minecraft_directory, "options.txt")
        if not os.path.exists(self.minecraft_options):
            # Create the file if it doesn't exist
            with open(self.minecraft_options, "w") as f:
                f.write("fullscreen:false\n")
        self._set_fullscreen()

    def _set_fullscreen(self):
        # Set the Minecraft options to fullscreen
        if not os.path.exists(self.minecraft_options):
            # Create the file with the fullscreen option if it doesn't exist
            with open(self.minecraft_options, "w") as f:
                f.write(f"fullscreen:{str(self.fullscreen).lower()}\n")
            return

        with open(self.minecraft_options, "r") as f:
            lines = f.readlines()

        with open(self.minecraft_options, "w") as f:
            for line in lines:
                if line.startswith("fullscreen:"):
                    f.write(f"fullscreen:{str(self.fullscreen).lower()}\n")


settings = Settings()
settings.load()
