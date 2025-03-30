import os
import asyncio
import subprocess

import flet as ft
import httpx
import minecraft_launcher_lib as mcl

from ..auth import account
from ..modpack import modpack
from ..authlib import authlib
from ..config import (
    MINECRAFT_FOLDER,
    SKINS_CACHE_FOLDER,
    LAUNCHER_DIRECTORY,
    JVM_ARGS,
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
)
from ..settings import settings


class MainPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/")
        self.page = page
        self.controls = []
        self._max_progress = 0
        self._download_callback = {  # lambda : self._progress_text.text = status,
            "setStatus": lambda status: self._set_progress_text(status),
            "setProgress": lambda progress: self._set_progress(progress),
            "setMax": lambda max: self._set_max(max),
        }
        self.build_ui()

    @staticmethod
    async def update_user_info(event: ft.RouteChangeEvent):
        await account.render_skin()

        event.page.views[0].pagelet.appbar.title = ft.Text(
            f"Привіт, {account.user['user']['players'][0]['name']}!",
            size=20,
            weight=ft.FontWeight.BOLD,
        )
        event.page.views[0].pagelet.appbar.leading.content.src = (
            f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-face.png"
        )
        event.page.update()

    async def create_user_info(self):
        await account.render_skin()
        self.page.update()

    def build_ui(self):
        changelog_text = httpx.get(
            "https://raw.githubusercontent.com/cubedvij/modpack/refs/heads/main/README.md"
        ).text
        self._changelog = ft.Markdown(
            changelog_text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        )
        self._appbar = ft.AppBar(
            toolbar_height=64,
            leading_width=64,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            title=ft.Text(
                f"...",
                size=20,
                weight=ft.FontWeight.BOLD,
            ),
            leading=ft.IconButton(
                padding=ft.Padding(12, 12, 12, 12),
                content=ft.Image(
                    src=None,
                    filter_quality=ft.FilterQuality.NONE,
                    fit=ft.ImageFit.CONTAIN,
                    width=64,
                    height=64,
                ),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    bgcolor=ft.Colors.TRANSPARENT,
                ),
                tooltip="Профіль",
                on_click=lambda e: self.page.go("/profile"),
            ),
            # bgcolor=ft.Colors.SURFACE,
            actions=[
                ft.Container(
                    # telegram
                    content=ft.Row(
                        [
                            # donate button
                            ft.IconButton(
                                padding=ft.Padding(12, 12, 12, 12),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                icon=ft.Icons.ATTACH_MONEY,
                                on_click=lambda e: self._open_link(
                                    "https://send.monobank.ua/jar/48bPzh2JmA"
                                ),
                                tooltip="Підтримати проект",
                            ),
                            ft.IconButton(
                                padding=ft.Padding(12, 12, 12, 12),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                icon=ft.Icons.TELEGRAM,
                                on_click=lambda e: self._open_link(
                                    "https://t.me/cube_dvij"
                                ),
                                tooltip="Telegram",
                            ),
                            # discord
                            ft.IconButton(
                                padding=ft.Padding(12, 12, 12, 12),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                icon=ft.Icons.DISCORD,
                                on_click=lambda e: self._open_link(
                                    "https://discord.gg/E9rZM58gqT"
                                ),
                                tooltip="Discord",
                            ),
                            # settings
                            ft.IconButton(
                                padding=ft.Padding(12, 12, 12, 12),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    bgcolor=ft.Colors.TRANSPARENT,
                                ),
                                icon=ft.Icons.SETTINGS,
                                on_click=lambda e: self.page.go("/settings"),
                                tooltip="Налаштування",
                            ),
                        ]
                    ),
                    padding=ft.Padding(0, 0, 8, 0),
                ),
            ],
            shape=ft.RoundedRectangleBorder(radius=8),
        )
        self._play_button = ft.FloatingActionButton(
            icon=ft.Icons.PLAY_ARROW,
            shape=ft.RoundedRectangleBorder(radius=8),
            text="Грати",
            width=160,
            on_click=self._check_game,
        )
        self._check_game_button = ft.FloatingActionButton(
            icon=ft.Icons.RESTART_ALT,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            shape=ft.RoundedRectangleBorder(radius=8),
            tooltip="Перевстановити гру",
            on_click=self._force_install_game,
        )
        self._open_game_folder_button = ft.FloatingActionButton(
            icon=ft.Icons.FOLDER,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            shape=ft.RoundedRectangleBorder(radius=8),
            tooltip="Відкрити папку з грою",
            on_click=lambda e: self._open_link(f"file://{MINECRAFT_FOLDER}"),
        )
        self.floating_action_button = ft.Container(
            ft.Row(
                [
                    self._play_button,
                    self._check_game_button,
                    self._open_game_folder_button,
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            padding=ft.Padding(0, 0, 8, 8),
        )
        self.floating_action_button_location = (
            ft.FloatingActionButtonLocation.CENTER_DOCKED
        )
        self._progress_text = ft.Text(
            "",
            size=20,
            color=ft.Colors.WHITE,
            visible=False,
        )
        self._progress_bar = ft.ProgressBar(value=0, visible=False)
        self._version_column = ft.Column(
            controls=[
                ft.Text(
                    f"Встановлена версія: {modpack.installed_version}",
                    size=12,
                    color=ft.Colors.WHITE,
                ),
                ft.Text(
                    f"Остання версія: {modpack.remote_version}",
                    size=12,
                    color=ft.Colors.WHITE,
                ),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )
        self.bottom_appbar = ft.BottomAppBar(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            self._progress_text,
                            self._progress_bar,
                        ],
                        expand=True,
                    ),
                    self._version_column,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=8,
                expand=True,
            ),
        )
        self.pagelet = ft.Pagelet(
            expand=True,
            expand_loose=True,
            appbar=self._appbar,
            # bottom_app_bar=self._bottom_bar,
            content=ft.Container(
                expand=True,
                padding=ft.Padding(0, 8, 0, 8),
                content=ft.Column(
                    controls=[self._changelog],
                    alignment=ft.MainAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        )
        self.controls.append(self.pagelet)
        self.page.update()

    def _check_game(self, event: ft.TapEvent):
        print("Checking game...")
        # check if game is installed
        installed_versions = mcl.utils.get_installed_versions(MINECRAFT_FOLDER)
        installed_versions_list = []
        for version in installed_versions:
            installed_versions_list.append(version["id"])
        print(f"Installed versions list: {installed_versions_list}")

        # check if game is installed
        if not all(
            (
                modpack.minecraft_version in installed_versions_list,
                modpack.modloader_full in installed_versions_list,
            )
        ):
            self._install_minecraft()
        # check if modpack version is latest
        elif not modpack.is_up_to_date():
            self._update_modpack()
        # check if modpack installed correctly
        elif not modpack.verify_installation():
            self._update_modpack()
        else:
            self._launch_minecraft(modpack.modloader_full)

    def _launch_minecraft(self, version):
        print("Game is already downloaded.")
        options = {
            "username": account.user["user"]["players"][0]["name"],
            "uuid": account.user["user"]["players"][0]["uuid"],
            "token": account.account["access_token"],
            "launcherName": LAUNCHER_NAME,
            "launcherVersion": LAUNCHER_VERSION,
            "customResolution": True,
            "resolutionWidth": str(settings.window_width),
            "resolutionHeight": str(settings.window_height),
        }
        options["jvmArguments"] = [
            f"-javaagent:{MINECRAFT_FOLDER}/authlib-injector.jar=https://auth.cubedvij.pp.ua/authlib-injector",
            f"-Xmx{settings.max_use_ram}M",
            f"-Xms{settings.min_use_ram}M",
            *settings.java_args,
        ]
        minecraft_command = mcl.command.get_minecraft_command(
            version, MINECRAFT_FOLDER, options
        )
        # change working directory to .minecraft
        os.chdir(MINECRAFT_FOLDER)
        self._minecraft_process = subprocess.Popen(minecraft_command)
        self.page.run_task(self._check_minecraft)
        self._play_button_stop()
        self._check_game_button_disable()
        if settings.minimize_launcher:
            self.page.window.minimized = True
        if settings.close_launcher:
            self.page.window.close()
        self.page.update()

    def _install_minecraft(self):
        print("Downloading game...")

        self._progress_bar.visible = True
        self._progress_text.visible = True

        self._play_button_disable()
        self._check_game_button_disable()
        self.page.update()

        self._set_progress_text("Встановлення authlib-injector...")
        authlib.download_latest_release(
            f"{MINECRAFT_FOLDER}/authlib-injector.jar",
            self._set_progress,
            self._set_max,
        )
        self._set_progress_text("authlib-injector встановлено")

        # install modpack
        self._set_progress_text("Встановлення модпаку...")
        modpack.install(
            MINECRAFT_FOLDER,
            self._download_callback,
        )

        self._progress_bar.visible = False
        self._progress_text.visible = False

        self._check_game_button_enable()
        self._play_button_enable()
        # update version column
        self._version_column.controls[0].value = (
            f"Встановлена версія: {modpack.installed_version}"
        )
        self._version_column.controls[1].value = (
            f"Остання версія: {modpack.remote_version}"
        )

        if self.page is not None:
            self.page.update()

    def _update_modpack(self):
        print("Updating modpack...")
        self._progress_bar.visible = True
        self._progress_text.visible = True

        self._play_button_disable()
        self._check_game_button_disable()
        self.page.update()

        self._set_progress_text("Оновлення модпаку...")
        modpack.update(
            self._download_callback,
        )

        self._progress_bar.visible = False
        self._progress_text.visible = False

        self._check_game_button_enable()
        self._play_button_enable()
        # update version column
        self._version_column.controls[0].value = (
            f"Встановлена версія: {modpack.installed_version}"
        )
        self._version_column.controls[1].value = (
            f"Остання версія: {modpack.remote_version}"
        )
        
        if self.page is not None:
            self.page.update()

    def _force_install_game(self, event: ft.TapEvent):
        latest_release = mcl.utils.get_latest_version()["release"]
        latest_forge = mcl.forge.find_forge_version(latest_release)
        latest_forge = latest_forge.replace("-", "-forge-", 1)
        self._install_minecraft(latest_release)

    def _stop_game(self, event: ft.TapEvent):
        self._minecraft_process.kill()
        # change working directory to launcher directory
        os.chdir(LAUNCHER_DIRECTORY)
        self._play_button_enable()
        self._check_game_button_enable()
        self.page.update()

    def _cancel_download(self, event: ft.TapEvent):
        self._check_game_button_enable()
        self._play_button_enable()
        self._progress_bar.value = 0
        self._progress_text.value = "Завантаження відмінено"
        self.page.update()

    def _set_progress_text(self, status: str):
        self._progress_text.value = status
        self._progress_text.update()

    def _set_progress(self, progress: int):
        if self._max_progress != 0:
            self._progress_bar.value = progress / self._max_progress
            self._progress_bar.update()

    def _play_button_disable(self):
        self._play_button.disabled = True
        self._play_button.text = "Завантаження..."
        self._play_button.bgcolor = ft.Colors.GREY_800
        self._play_button.icon = ft.Icons.CLOUD_DOWNLOAD

    def _play_button_enable(self):
        self._play_button.disabled = False
        self._play_button.text = "Грати"
        self._play_button.bgcolor = ft.Colors.PRIMARY_CONTAINER
        self._play_button.icon = ft.Icons.PLAY_ARROW
        self._play_button.on_click = self._check_game

    def _play_button_stop(self):
        self._play_button.disabled = False
        self._play_button.text = "Зупинити"
        self._play_button.bgcolor = ft.Colors.RED_ACCENT_700
        self._play_button.icon = ft.Icons.STOP
        self._play_button.on_click = self._stop_game

    def _check_game_button_disable(self):
        self._check_game_button.disabled = True
        self._check_game_button.bgcolor = ft.Colors.GREY_800
        self._check_game_button.icon = ft.Icons.RESTART_ALT

    def _check_game_button_enable(self):
        self._check_game_button.disabled = False
        self._check_game_button.bgcolor = ft.Colors.SECONDARY_CONTAINER
        self._check_game_button.icon = ft.Icons.RESTART_ALT
        self._check_game_button.on_click = self._force_install_game

    def _check_game_button_stop(self):
        self._check_game_button.disabled = False
        self._check_game_button.bgcolor = ft.Colors.RED_ACCENT_700
        self._check_game_button.icon = ft.Icons.STOP
        self._check_game_button.on_click = self._cancel_download

    def _check_minecraft_running(self):
        if self._minecraft_process is not None:
            if self._minecraft_process.poll() is None:
                return True
        return False

    # if minecraft is not running, enable play button, check in loop
    async def _check_minecraft(self):
        while True:
            if not self._check_minecraft_running():
                self._play_button_enable()
                self._check_game_button_enable()
                self.page.window.minimized = False
                self.page.update()
                break
            await asyncio.sleep(2)

    def _set_max(self, max: int):
        self._max_progress = max

    def _open_link(self, link: str):
        if os.name == "nt":
            os.system(f"start {link}")
        else:
            os.system(f"xdg-open {link}")
