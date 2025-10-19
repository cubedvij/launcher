import flet as ft

from routes import LoginPage, MainPage, ProfilePage, RegisterPage, SettingsPage
from settings import settings
from utils import setup_theme_settings
from config import (
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
    WINDOW_SIZE,
)


async def main(page: ft.Page):
    page.title = f"{LAUNCHER_NAME} {LAUNCHER_VERSION}"
    page.window.width, page.window.height = WINDOW_SIZE
    page.window.min_width, page.window.min_height = WINDOW_SIZE
    page.window.center()
    
    page.theme_mode = settings.launcher_theme
    
    setup_theme_settings(
        page,
        settings.launcher_color,
        settings.launcher_border_radius,
        settings.launcher_border_shape,
    )

    page.window.visible = True
    page.window.prevent_close = False

    views = {
        "/": MainPage(page),
        "/login": LoginPage(page),
        "/register": RegisterPage(page),
        "/profile": ProfilePage(page),
        "/settings": SettingsPage(page),
    }

    async def route_change(event: ft.RouteChangeEvent):
        page.views.clear()
        page.views.append(views[event.route])
        if event.route == "/":
            await views[event.route].update_user_info(event)
        if event.route == "/profile":
            await views[event.route].update_user_info(event)
        if event.route == "/settings":
            await views[event.route].reload_settings()
        page.update()

    page.on_route_change = route_change
    from auth import account

    if await account.avalidate() and await account.aget_user():
        page.go("/")
    else:
        page.go("/login")


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
