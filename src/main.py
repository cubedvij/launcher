import logging

import flet as ft

from routes import LoginPage, MainPage, ProfilePage, RegisterPage, SettingsPage

from updater import updater
from config import (
    _COMPILED,
    APPDATA_FOLDER,
    LAUNCHER_DIRECTORY,
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
    WINDOW_SIZE,
)

if _COMPILED:
    logging.basicConfig(
        filename=APPDATA_FOLDER / "launcher.log",
        level=logging.INFO,
        # make it more readable for the user
        format="%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s",
        datefmt="%H:%M:%S",

    )
    logging.getLogger("flet_core").setLevel(logging.INFO)
    # HACK: Remove old MEIPASS folder
    updater.clear_old_meipass()
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

    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.DEEP_PURPLE,
        page_transitions=ft.PageTransitionsTheme(
            linux=ft.PageTransitionTheme.FADE_FORWARDS,
            windows=ft.PageTransitionTheme.FADE_FORWARDS
        )
    )
    page.window.visible = True
    page.window.prevent_close = False

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
    from auth import account

    if await account.avalidate() and await account.aget_user():
        page.go("/")
    else:
        page.go("/login")

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
