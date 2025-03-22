import flet as ft

from src.auth import account
from src.routes import LoginPage, MainPage, RegisterPage, ProfilePage, SettingsPage

# Fix SSL on Linux
import certifi
import os

os.environ["SSL_CERT_FILE"] = certifi.where()

WINDOW_SIZE = (900, 540)

def main(page: ft.Page):
    page.title = "Кубічний Лаунчер" 
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
    ft.app(main)