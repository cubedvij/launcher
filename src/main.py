import logging

import flet as ft

from auth import account
from config import (
    _COMPILED,
    APPDATA_FOLDER,
    LAUNCHER_DIRECTORY,
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
    WINDOW_SIZE,
)
from routes import LoginPage, MainPage, ProfilePage, RegisterPage, SettingsPage

if _COMPILED:
    logging.basicConfig(
        filename=APPDATA_FOLDER / "launcher.log",
        level=logging.INFO,
        # make it more readable for the user
        format="%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s",
        datefmt="%H:%M:%S",

    )
    logging.getLogger("flet_core").setLevel(logging.INFO)
else:
    logging.basicConfig(
        level=logging.INFO,
        # make it more readable for the user
        format="%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("flet_core").setLevel(logging.INFO)

logging.info(f"Launcher version: {LAUNCHER_VERSION}")
logging.info(f"Launcher directory: {LAUNCHER_DIRECTORY}")

async def main(page: ft.Page):
    page.title = f"{LAUNCHER_NAME} {LAUNCHER_VERSION}"
    page.window.width, page.window.height = WINDOW_SIZE
    page.window.min_width, page.window.min_height = WINDOW_SIZE
    page.window.center()
    
    page.window.visible = True
    page.window.prevent_close = False
    page.update()
    
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
        

ft.app(main, view=ft.AppView.FLET_APP_HIDDEN)