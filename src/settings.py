import os
import json

from config import RAM_SIZE, JVM_ARGS, APPDATA_FOLDER


class GameSettings:
    fullscreen: bool
    window_width: int
    window_height: int
    min_use_ram: int
    max_use_ram: int
    java_args: list[str]

    def from_dict(self, data: dict):
        self.fullscreen = data.get("fullscreen", False)
        self.window_width = data.get("window_width", 854)
        self.window_height = data.get("window_height", 480)
        self.min_use_ram = data.get("min_use_ram",  min(RAM_SIZE // 2, 6 * 1024))
        self.max_use_ram = data.get("max_use_ram", self.min_use_ram)
        self.java_args = data.get("java_args", JVM_ARGS)

    def to_dict(self) -> dict:
        return {
            "fullscreen": self.fullscreen,
            "min_use_ram": self.min_use_ram,
            "max_use_ram": self.max_use_ram,
            "java_args": self.java_args,
        }


class Settings:
    def __init__(self):
        self._settings_file = os.path.join(APPDATA_FOLDER, "settings.json")
        # Game settings
        self.minecraft_directory = APPDATA_FOLDER / ".minecraft"
        self.modpack_name = "main"
        self.minecraft_options = os.path.join(
            self.minecraft_directory, "modpacks", self.modpack_name, "options.txt"
        )
        self.launcher_theme = "system"
        self.launcher_color = "deeppurple"
        self.launcher_border_radius = 8
        self.launcher_border_shape = "roundedRectangle"
        self.minimize_launcher = True
        self.close_launcher = False

        self.game = GameSettings()

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

                self.minimize_launcher = launcher_data.get(
                    "minimize", self.minimize_launcher
                )
                self.close_launcher = launcher_data.get("close", self.close_launcher)
                self.game.from_dict(minecraft_data.get(self.modpack_name, {}))
                self.minecraft_directory = minecraft_data.get(
                    "directory", str(self.minecraft_directory)
                )
                if not os.path.exists(self.minecraft_directory):
                    os.makedirs(self.minecraft_directory)
        else:
            self.save()

    def save(self):
        with open(self._settings_file, "r") as f:
            data = json.load(f)
            other_modpacks_settings = {
                k: v
                for k, v in data.get("minecraft", {}).items()
                if k != self.modpack_name and k != "directory"
            }

        launcher_data = {
            "theme": self.launcher_theme,
            "color": self.launcher_color,
            "border_radius": int(self.launcher_border_radius),
            "border_shape": self.launcher_border_shape,
            "minimize": self.minimize_launcher,
            "close": self.close_launcher,
        }

        minecraft_data = {
            self.modpack_name: {
                "fullscreen": self.game.fullscreen,
                "window_width": self.game.window_width,
                "window_height": self.game.window_height,
                "min_use_ram": self.game.min_use_ram,
                "max_use_ram": self.game.max_use_ram,
                "java_args": self.game.java_args,
            },
            **other_modpacks_settings,
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
        self._set_fullscreen()

    def _set_fullscreen(self):
        # Set the Minecraft options to fullscreen
        if not os.path.exists(self.minecraft_options):
            # Create the file with the fullscreen option if it doesn't exist
            with open(self.minecraft_options, "w") as f:
                f.write(f"fullscreen:{str(self.game.fullscreen).lower()}\n")
            return

        with open(self.minecraft_options, "r") as f:
            lines = f.readlines()

        # apply fullscreen setting
        with open(self.minecraft_options, "w") as f:
            for line in lines:
                if line.startswith("fullscreen:"):
                    f.write(f"fullscreen:{str(self.game.fullscreen).lower()}\n")
                else:
                    f.write(line)

    def _load_fullscreen(self):
        if not os.path.exists(self.minecraft_options):
            self.game.fullscreen = False
            return

        with open(self.minecraft_options, "r") as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith("fullscreen:"):
                value = line.split(":", 1)[1].strip().lower()
                self.game.fullscreen = value == "true"
                return
        else:
            self.game.fullscreen = False
            self._set_fullscreen()


settings = Settings()
settings.load()
