import os
import logging
import asyncio
import subprocess

import httpx
import flet as ft
from nava import play

from minestat import MineStat, SlpProtocols

from utils import Shimmer, _open_link
from auth import account
from modpack import modpack
from authlib import authlib
from updater import updater
from stats import stats
from config import (
    BASE_PATH,
    SERVER_IP,
    SKINS_CACHE_FOLDER,
    LAUNCHER_DIRECTORY,
    CHANGELOG_URL,
    SYSTEM_OS,
)
from settings import settings


class MainPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/")
        self.page = page
        self.controls = []
        self._keypressed_list = []
        self._game_started = False
        self._minecraft_process = None
        self._max_progress = 0
        self._download_callback = {  # lambda : self._progress_text.text = status,
            "setStatus": lambda status: self._set_progress_text(status),
            "setProgress": lambda progress: self._set_progress(progress),
            "setMax": lambda max: self._set_max(max),
        }
        self.build_ui()
        self._latest_tasks_inited = None
        self.page.run_task(self.init_tasks)
        self.page.on_keyboard_event = self.on_keyboard_event
        self.page.window.on_event = self.on_window_event

    async def init_tasks(self):
        while True:
            if (
                self._latest_tasks_inited
                and self.page
                and (self.page.loop.time() - self._latest_tasks_inited < 60)
            ):
                await asyncio.sleep(60)
            break
        self._server_status_task = self.page.run_task(self._server_status_update)
        self._check_launcher_updates_task = self.page.run_task(
            self._check_launcher_updates
        )
        self._check_modpack_update_task = self.page.run_task(
            self._check_modpack_update_async
        )
        # self._playtime_update_task = self.page.run_task(self._playtime_update)
        self._latest_tasks_inited = self.page.loop.time()

    async def on_window_event(self, event: ft.WindowEvent):
        if (
            event.type == ft.WindowEventType.MINIMIZE
            # or event.type == ft.WindowEventType.HIDE
            # or event.type == ft.WindowEventType.BLUR
        ):
            # kill all tasks when window is minimized
            self._server_status_task.cancel()
            self._check_launcher_updates_task.cancel()
            self._check_modpack_update_task.cancel()
            # self._playtime_update_task.cancel()
            self._latest_tasks_inited = None
        elif (
            event.type == ft.WindowEventType.FOCUS
            # or event.type == ft.WindowEventType.RESTORE
        ):
            # restart tasks when window is restored
            if self._latest_tasks_inited is None:
                self.page.run_task(self.init_tasks)
        elif event.type == ft.WindowEventType.SHOW:
            # restart tasks when window is shown
            if self._latest_tasks_inited is None:
                self.page.run_task(self.init_tasks)
        elif event.type == ft.WindowEventType.CLOSE:
            self.kill_app()

    async def on_keyboard_event(self, event: ft.KeyboardEvent):
        # check iddqd
        self._keypressed_list.append(event.key)
        if len(self._keypressed_list) > 5:
            self._keypressed_list.pop(0)
        if self._keypressed_list == ["I", "D", "D", "Q", "D"]:
            self._keypressed_list = []
            play(os.path.join(BASE_PATH, "assets", "iddqd.wav"), async_mode=True)
            event.page.views[0].pagelet.appbar.leading.content = ft.Image(
                src="iddqd.png",
                filter_quality=ft.FilterQuality.NONE,
                fit=ft.ImageFit.CONTAIN,
                width=64,
                height=64,
            )
            self.page.update()

    async def _check_launcher_updates(self):
        if await updater.check_for_update():
            logging.info(f"Latest version found: {updater.latest_version}")
            logging.info(f"Latest download URL: {updater.latest_download_url}")
            self.page.open(self._update_banner)
            self.page.update()

    async def _check_modpack_update_async(self):
        await asyncio.to_thread(self._check_modpack_update, force=True)
        while True:
            await asyncio.sleep(60)
            await asyncio.to_thread(self._check_modpack_update)

    def _check_modpack_update(self, force: bool = False):
        if self.page:
            modpack._fetch_latest_index(force=force)
            if modpack.is_up_to_date():
                return
            if modpack.installed_version == "unknown":
                self._version_tooltip.message = (
                    "Модпак не встановлено. Натисніть, щоб встановити його."
                )
                self._play_button_install()
                self.page.update()
                return

            self._version_tooltip.message = f"Доступне оновлення: {modpack.installed_version} -> {modpack.remote_version}"
            self._play_button_update()
            # update changelog
            self._get_changelog()
            self.page.update()

    @staticmethod
    async def update_user_info(event: ft.RouteChangeEvent):
        await account.render_skin()

        event.page.views[0].pagelet.appbar.title = ft.Text(
            f"Вітаю, {account.user['user']['players'][0]['name']}!",
            size=20,
            weight=ft.FontWeight.BOLD,
        )
        event.page.views[0].pagelet.appbar.leading.content = ft.Image(
            src=f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-face.png",
            filter_quality=ft.FilterQuality.NONE,
            fit=ft.ImageFit.CONTAIN,
            width=64,
            height=64,
        )

    async def create_user_info(self):
        await account.render_skin()
        self.page.update()

    def _install_update(self):
        self.page.close(self._update_banner)
        self.update_modal = ft.AlertDialog(
            modal=True,
            content=ft.Row(
                [ft.ProgressRing(), ft.Text("Завантаження оновлення...")],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions_padding=ft.Padding(0, 0, 0, 0),
            open=True,
        )
        self.page.overlay.append(self.update_modal)
        self.page.update()
        updater.download_update()
        logging.info("Update downloaded successfully.")
        self.page.overlay.remove(self.update_modal)
        self.page.update()
        self.kill_app()
        logging.info("Launcher exited.")

    def kill_app(self):
        logging.info("Trying to exit program via asyncio")
        to_cancel = asyncio.all_tasks(self.page.loop)
        if not to_cancel:
            return
        logging.info(f"Canceling {len(to_cancel)} tasks")
        for task in to_cancel:
            task.cancel()

    def _get_changelog(self):
        changelog_text = httpx.get(
            CHANGELOG_URL,
            timeout=5,
            follow_redirects=True,
        ).text
        self._changelog = ft.Markdown(
            value=changelog_text,
            auto_follow_links=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        )
        # remove all
        self.pagelet.content.content.controls.clear()
        # add new _changelog
        self.pagelet.content.content.controls.append(self._changelog)

    def _change_modpack(self, event: ft.ControlEvent):
        selected_modpack = event.control.value
        if selected_modpack not in modpack._remote_modpacks:
            logging.error(f"Selected modpack {selected_modpack} not found.")
            return
        modpack.set_modpack(selected_modpack)
        # self._check_modpack_update(force=True)
        self.page.update()

    def __open_monobank(self, event: ft.TapEvent):
        play(os.path.join(BASE_PATH, "assets", "mono.wav"), async_mode=True)
        _open_link("https://send.monobank.ua/jar/48bPzh2JmA")

    def build_ui(self):
        self._update_banner = ft.Banner(
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            content=ft.Text(
                "Ваша версія лаунчера застаріла. Оновити до останньої версії?",
            ),
            leading=ft.Icon(
                name=ft.Icons.UPDATE,
                color=ft.Colors.SECONDARY,
            ),
            actions=[
                ft.TextButton("Так", on_click=lambda e: self._install_update()),
                ft.TextButton(
                    "Ні",
                    on_click=lambda e: self.page.close(self._update_banner),
                ),
            ],
        )
        self._changelog = Shimmer(
            control=ft.Column(
                controls=[
                    ft.Text(
                        "Завантаження чейнджлогу...",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
        )
        self._appbar = ft.AppBar(
            toolbar_height=64,
            leading_width=64,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            title=Shimmer(
                control=ft.Text(
                    "Завантаження...",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            leading=ft.IconButton(
                content=Shimmer(
                    control=ft.Icon(ft.Icons.PERSON, size=32),
                    color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    width=64,
                    height=64,
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
                                icon=ft.Icons.ATTACH_MONEY,
                                on_click=self.__open_monobank,
                                tooltip="Підтримати проект",
                            ),
                            # github
                            ft.IconButton(
                                content=ft.Image(
                                    src="github-mark.svg",
                                    width=20,
                                    height=20,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                on_click=lambda e: _open_link(
                                    "https://github.com/cubedvij"
                                ),
                                tooltip="GitHub",
                            ),
                            ft.IconButton(
                                icon=ft.Icons.TELEGRAM,
                                on_click=lambda e: _open_link("https://t.me/cube_dvij"),
                                tooltip="Telegram",
                            ),
                            # discord
                            ft.IconButton(
                                icon=ft.Icons.DISCORD,
                                on_click=lambda e: _open_link(
                                    "https://discord.gg/E9rZM58gqT"
                                ),
                                tooltip="Discord",
                            ),
                            # settings
                            ft.IconButton(
                                icon=ft.Icons.SETTINGS,
                                on_click=lambda e: self.page.go("/settings"),
                                tooltip="Налаштування",
                            ),
                        ]
                    ),
                    padding=ft.Padding(0, 0, 8, 0),
                ),
            ],
        )
        self._version_tooltip = ft.Tooltip(
            f"Встановлено останню версію: {modpack.installed_version}",
        )
        self._play_button = ft.FloatingActionButton(
            icon=ft.Icons.PLAY_ARROW,
            text="Грати",
            tooltip=self._version_tooltip,
            width=160,
            on_click=self._check_game,
        )
        self._check_game_button = ft.FloatingActionButton(
            icon=ft.Icons.RESTART_ALT,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            tooltip="Перевстановити гру",
            on_click=self._force_install_game,
        )
        self._open_game_folder_button = ft.FloatingActionButton(
            icon=ft.Icons.FOLDER,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            tooltip="Відкрити папку з грою",
            on_click=lambda e: _open_link(f"file://{settings.minecraft_directory}"),
        )
        self._selected_modpack = ft.Dropdown(
            options=[
                ft.dropdown.Option(name) for name in modpack._remote_modpacks
            ],
            on_change=self._change_modpack,
            value=modpack._selected,
            fill_color=ft.Colors.SECONDARY_CONTAINER,
            width=292,
            filled=True,
        )
        self.floating_action_button = ft.Container(
                    ft.Row(
                        [
                            self._play_button,
                            self._check_game_button,
                            self._open_game_folder_button,
                            self._selected_modpack,
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        expand=False,
                    ),
            padding=ft.Padding(0, 0, 8, 8),
            expand=False,
        )
        self.floating_action_button_location = (
            ft.FloatingActionButtonLocation.MINI_CENTER_DOCKED
        )
        self._progress_text = ft.Text(
            "",
            size=20,
            visible=False,
        )
        self._progress_bar = ft.ProgressBar(value=0, visible=False)
        self._server_status = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            name=ft.Icons.CIRCLE,
                            color=ft.Colors.ORANGE,
                            size=16,
                        ),
                        ft.Text(
                            "Сервер офлайн",
                            size=12,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(
                            name=ft.Icons.PERSON,
                            size=16,
                        ),
                        ft.Text(
                            "Онлайн гравців:",
                            size=12,
                        ),
                        ft.Text(
                            "",
                            size=12,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
        self._playtime_text = ft.Text(
            "Час на сервері: -",
            size=12,
        )
        self._latest_online_text = ft.Text(
            "Останній вхід: -",
            size=12,
        )
        self._playtime = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            name=ft.Icons.ACCESS_TIME,
                            size=16,
                        ),
                        self._playtime_text,
                    ],
                    spacing=4,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(
                            name=ft.Icons.PLAY_ARROW,
                            size=16,
                        ),
                        self._latest_online_text,
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.START,
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
                    self._server_status,
                    ft.Container(width=292),
                    # self._playtime,
                ],
                expand=False,
            ),
        )
        self.pagelet = ft.Pagelet(
            expand=True,
            appbar=self._appbar,
            # bottom_app_bar=self._bottom_bar,
            content=ft.Container(
                padding=ft.Padding(0, 8, 0, 8),
                content=ft.Column(
                    controls=[self._changelog],
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        )
        self.controls.append(self.pagelet)
        self.page.run_thread(self._get_changelog)
        self.page.update()

    async def _server_status_update(self):
        while True:
            try:
                await asyncio.to_thread(self._update_server_status)
                await asyncio.sleep(10)
            except Exception as e:
                logging.info(f"Error updating server status: {e}")
                await asyncio.sleep(15)

    async def _playtime_update(self):
        while True:
            try:
                if self.page is None:
                    return
                player_stats = await stats.get_player_stats(
                    account.user["user"]["players"][0]["uuid"]
                )
                if player_stats is None:
                    self._playtime_text.value = "Час на сервері: -"
                    self._latest_online_text.value = "Останній вхід: -"
                    await asyncio.sleep(60)
                    continue
                player_stats = player_stats.get("info", {})
                playtime = player_stats.get("playtime", "0")
                last_seen = player_stats.get("last_seen", "Ніколи")
                if player_stats is not None:
                    self._playtime_text.value = f"Час на сервері: {playtime}"
                    self._latest_online_text.value = f"Останній вхід: {last_seen}"
            except Exception as e:
                logging.error(f"Error updating playtime: {e}")
            await asyncio.sleep(60)  # Update every minute

    def _update_server_status(self):
        if self.page is None:
            return
        try:
            server = MineStat(
                address=SERVER_IP, port=25565, query_protocol=SlpProtocols.LEGACY
            )
        except Exception as e:
            logging.warning(f"Failed to fetch server status: {e}")
            return

        if server.online:
            self._server_status.controls[0].controls[0].color = ft.Colors.GREEN
            self._server_status.controls[0].controls[
                1
            ].value = f"Сервер онлайн ({server.latency} мс)"
            self._server_status.controls[1].controls[
                2
            ].value = f"{server.current_players}/{server.max_players}"
        else:
            self._server_status.controls[0].controls[0].color = ft.Colors.RED
            self._server_status.controls[0].controls[1].value = "Сервер офлайн"
            self._server_status.controls[1].controls[2].value = "-"

        if self.page:
            self.page.update()

    def _check_game(self, event: ft.TapEvent):
        self._play_button_disabled()
        self._check_game_button_disable()
        self.page.update()

        if self._check_minecraft_running():
            logging.info("Minecraft is already running.")
            return

        logging.info("Checking game...")
        # check if game is installed
        installed_versions = modpack.get_installed_versions()
        installed_versions_list = []
        for version in installed_versions:
            installed_versions_list.append(version["id"])
        logging.info(f"Installed versions list: {installed_versions_list}")

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
            self._update_modpack(event)
        # check if modpack installed correctly
        elif not modpack.verify_installation():
            self._update_modpack(event)
        else:
            self._launch_minecraft()

    def _launch_minecraft(self):
        # options = {
        #     "username": account.user["user"]["players"][0]["name"],
        #     "uuid": account.user["user"]["players"][0]["uuid"],
        #     "token": account.account["access_token"],
        #     "launcherName": LAUNCHER_NAME,
        #     "launcherVersion": LAUNCHER_VERSION,
        #     "customResolution": True,
        #     "resolutionWidth": str(settings.window_width),
        #     "resolutionHeight": str(settings.window_height),
        # }
        minecraft_command = modpack.get_minecraft_command(
            account.username, account.uuid, account.access_token
        )
        if self._check_minecraft_running():
            logging.info("Minecraft is already running.")
            return
        if SYSTEM_OS == "Windows":
            self._minecraft_process = subprocess.Popen(
                minecraft_command,
                cwd=modpack.modpack_path,
                creationflags=subprocess.CREATE_NO_WINDOW,
                start_new_session=True,
            )
        elif SYSTEM_OS == "Linux":
            self._minecraft_process = subprocess.Popen(
                minecraft_command,
                cwd=modpack.modpack_path,
                start_new_session=True,
            )
        self.page.run_task(self._check_minecraft)
        self._play_button_stop()
        self._check_game_button_disable()
        if settings.minimize_launcher:
            self.page.window.minimized = True
        if settings.close_launcher:
            self.kill_app()
        self.page.update()

    def _install_minecraft(self):
        logging.info("Downloading game...")

        self._progress_bar.visible = True
        self._progress_text.visible = True

        self._play_button_download()
        self._check_game_button_disable()
        self.page.update()

        self._set_progress_text("Встановлення authlib-injector...")
        if not authlib.download_latest_release(
            f"{settings.minecraft_directory}/authlib-injector.jar",
            self._download_callback,
        ):
            logging.error("Failed to download authlib-injector.")
            self._set_progress_text("Не вдалося завантажити authlib-injector.")
            self._progress_bar.visible = False
            self._progress_text.visible = False
            self._play_button_enable()
            self._check_game_button_enable()
            return

        logging.info("authlib-injector downloaded successfully.")
        self._set_progress_text("authlib-injector встановлено")

        # install modpack
        self._set_progress_text("Встановлення модпаку...")
        if not modpack.install(
            self._download_callback,
        ):
            logging.error("Failed to install modpack.")
            self._set_progress_text("Не вдалося встановити модпак. Перевірте лог.")
            self._progress_bar.visible = False
            # self._progress_text.visible = False
            self._play_button_enable()
            self._check_game_button_enable()
            return

        logging.info("Modpack installed successfully.")
        # self._set_progress_text("Модпак встановлено")

        self._progress_bar.visible = False
        self._progress_text.visible = False

        self._check_game_button_enable()
        self._play_button_enable()
        # update version tooltip
        self._version_tooltip.message = (
            f"Встановлено останню версію: {modpack.installed_version}"
        )
        if self.page is not None:
            self.page.update()

    def _update_modpack(self, event: ft.TapEvent):
        logging.info("Updating modpack...")
        self._progress_bar.visible = True
        self._progress_text.visible = True

        self._play_button_download()
        self._check_game_button_disable()
        self.page.update()

        self._set_progress_text("Оновлення модпаку...")
        modpack.update(
            self._download_callback,
        )
        logging.info("Modpack updated successfully.")
        self._set_progress_text("Модпак оновлено")
        self._progress_bar.visible = False
        # self._progress_text.visible = False

        self._check_game_button_enable()
        self._play_button_enable()
        # update version column
        self._version_tooltip.message = (
            f"Встановлено останню версію: {modpack.installed_version}"
        )

        if self.page is not None:
            self.page.update()

    def _force_install_game(self, event: ft.TapEvent):
        modpack._fetch_latest_index()
        self._install_minecraft()

    def _stop_game(self, event: ft.TapEvent):
        if not self._check_minecraft_running():
            return
        try:
            self._minecraft_process.kill()
        except Exception as e:
            logging.error(f"Failed to kill Minecraft process: {e}")
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
        self._progress_text.value = status[:50] + "..." if len(status) > 50 else status
        if self._progress_text is None or self.page is None:
            return
        self._progress_text.update()

    def _set_progress(self, progress: int):
        if self._max_progress != 0:
            self._progress_bar.value = progress / self._max_progress
        if self.page is None or self._progress_bar is None:
            return
        self._progress_bar.update()

    def _play_button_download(self):
        self._play_button.disabled = True
        self._play_button.text = "Завантаження"
        self._play_button.bgcolor = ft.Colors.GREY_800
        self._play_button.icon = ft.Icons.DOWNLOADING

    def _play_button_disabled(self):
        self._play_button.disabled = True
        self._play_button.text = "Запуск..."
        self._play_button.bgcolor = ft.Colors.GREY_800
        self._play_button.icon = ft.Icons.HOURGLASS_TOP

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

    def _play_button_update(self):
        self._play_button.disabled = False
        self._play_button.text = "Оновити"
        self._play_button.bgcolor = ft.Colors.PRIMARY_CONTAINER
        self._play_button.icon = ft.Icons.UPDATE
        self._play_button.on_click = self._update_modpack

    def _play_button_install(self):
        self._play_button.disabled = False
        self._play_button.text = "Встановити"
        self._play_button.bgcolor = ft.Colors.PRIMARY_CONTAINER
        self._play_button.icon = ft.Icons.DOWNLOAD
        self._play_button.on_click = self._force_install_game

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
        return (
            self._minecraft_process is not None
            and self._minecraft_process.poll() is None
        )

    # if minecraft is not running, enable play button, check in loop
    async def _check_minecraft(self):
        while True:
            if not self._check_minecraft_running():
                self._play_button_enable()
                self._check_game_button_enable()
                self.page.window.to_front()
                self.page.update()
                break
            await asyncio.sleep(2)

    def _set_max(self, max: int):
        self._max_progress = max
        self._progress_bar.value = 0
        if self.page is None or self._progress_bar is None:
            return
        self._progress_bar.update()

    def _open_link(self, link: str):
        if os.name == "nt":
            subprocess.Popen(f'explorer /select,"{link}"')
        else:
            subprocess.Popen(["xdg-open", link])
