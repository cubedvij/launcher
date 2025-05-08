import logging

import flet as ft

from src.auth import account
from src.routes import LoginPage, MainPage, RegisterPage, ProfilePage, SettingsPage
from src.config import WINDOW_SIZE, LAUNCHER_NAME, LAUNCHER_VERSION, _COMPILED, APPDATA_FOLDER

# Fix SSL on Linux
import certifi
import os

os.environ["SSL_CERT_FILE"] = certifi.where()

if _COMPILED:
    logging.basicConfig(
        filename=APPDATA_FOLDER / "launcher.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("flet_core").setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)
    logging.debug(f"Launcher version: {LAUNCHER_VERSION}")
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("flet_core").setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)
    logging.debug(f"Launcher version: {LAUNCHER_VERSION}")


def main(page: ft.Page):
    page.title = f"{LAUNCHER_NAME} v{LAUNCHER_VERSION}"
    page.window.width, page.window.height = WINDOW_SIZE
    # page.window.min_width, page.window.min_height = WINDOW_SIZE
    # page.window.max_width, page.window.max_height = WINDOW_SIZE
    page.window.center()

    views = {
        "/": MainPage(page),
        "/login": LoginPage(page),
        "/register": RegisterPage(page),
        "/profile": ProfilePage(page),
        "/settings": SettingsPage(page)
    }

    async def route_change(event: ft.RouteChangeEvent):
        page.views.clear()
        page.views.append(views[event.route])
        if event.route == "/":
            await views[event.route].update_user_info(event)
        if event.route == "/profile":
            await views[event.route].update_user_info(event)
        page.update()

    page.on_route_change = route_change
    if account.validate() and account.get_user():
        page.go("/")
    else:
        page.go("/login")
        
if __name__ == "__main__":
    ft.app(main, assets_dir=os.path.join(os.path.dirname(__file__), "assets"))