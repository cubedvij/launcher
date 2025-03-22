import os
import asyncio
import subprocess

import flet as ft
import minecraft_launcher_lib as mcl

from ..auth import account
from ..authlib import authlib
from ..config import MINECRAFT_FOLDER, SKINS_CACHE_FOLDER


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
        self._changelog = ft.Markdown(
            """
Мар'яна Безугла дрочить член своїми величезними розпусними цицьками, міцно стискаючи їх у руках. Дві колосальні висячі дійки ритмічно ковзають по налитому прутню, готовому вибухнути спермою у будь-який момент. "Їби моє суче вим'я!" — кричить збожеволіла від хіті молодиця, шкірячи зуби — "Їби ці блудні цицьки, ЇБИ!" Погляд Мар'яни переходить на напружений пурпуровий гилун, і ніжно облизнувшись та застогнавши, вона кусає м'ясну сливу, через що булькаючий секрет прискає їй в горлянку.

Величезні. Четвертий розмір. Вона спеціально носить мішки, щоб у ній не бачили сексуальний об'єкт – сама так говорила. Соромиться своїх блудних безсоромних стрибаючих цицьок, які потребують чужих жадібних вуст. Так і бачу як вона пхикає від знемоги, поки в її дійки, відтягуючи в різні боки, всмоктуються чоловіки

Ти ще не бачив як Мар'яна стогнучи і хнюпаючи знесилено хапалася за чоловічі руки, намагаючись припинити безжалісна дійку своїх стиглих цицьок.

Просто намащені руки по черзі надобвали Мар'янині висячі цицьки, поки та зі сльозами на очах намагалася розтиснути цупкі кисті та визволити своє вим'я. "Ихих их не треба будь ласка", червоне обличчя Безуглої зі сльозами на очах, тремтячі губи, благаючи підняті брови — вона стогнала і хникала, часом фиркаючи і закочуючи очі від солодкої муки. Чоловік міцно стискав цицьки, ритмічно смикаючи їх униз, і з шалено стоячих, стирчащих сосків в емальоване відро починала капати молозія. Піхва Мар'яни розкрилася і текла, і вона боялася, що їй починає подобається доїння.

Та там як завжди. Очманівши від страждання і підступної втіхи, вона перестає чинити опір. Закотивши очі і видавши низький грудний стогін ОООООООООО, Мар'яна вигнула грудну клітку, відкинувши голову, і з стирчащих сосків туго линуло молоко. Мліючи в стогінах, Безугла крутила плечима, трусячи головою із закоченими очима. Мокра піхва заливалася мастилом, принадно розкрившись, і нарешті отримала своє. Залишивши змучені цицьки, мучитель ввів натруджений член в тремтячу розкішницю. Мар'яна скрикнула, і після кількох фрикцій з дикими стогонами вибризкнула порцію сечі. Тіло її шалено тремтіло від млості, і чоловік знову і знову встромляв член у піхву, в той час як молоко продовжувало бризкати з налитих надрочених дійок.
            """,
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
            width=184,
            on_click=self._check_game,
        )
        self._check_game_button = ft.FloatingActionButton(
            icon=ft.Icons.RESTART_ALT,
            shape=ft.RoundedRectangleBorder(radius=8),
            tooltip="Перевірити гру",
            on_click=self._force_check_game,
        )
        self._open_game_folder_button = ft.FloatingActionButton(
            icon=ft.Icons.FOLDER,
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
        self._progress_bar = ft.ProgressBar(expand=True, value=0, visible=False)

        self.bottom_appbar = ft.BottomAppBar(
            content=ft.Column(
                controls=[
                    self._progress_text,
                    self._progress_bar,
                ]
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
        latest_release = mcl.utils.get_latest_version()["release"]
        latest_forge = mcl.forge.find_forge_version(latest_release)
        installed_versions = mcl.utils.get_installed_versions(MINECRAFT_FOLDER) # {'id': '1.21.4', 'type': 'release', 'releaseTime': datetime.datetime(2024, 12, 3, 10, 12, 57, tzinfo=datetime.timezone.utc), 'complianceLevel': 1}, {'id': '1.21.4-forge-54.1.3', 'type': 'release', 'releaseTime': datetime.datetime(2025, 3, 17, 0, 9, 59, tzinfo=datetime.timezone.utc), 'complianceLevel': 0}]
        print(f"Latest release: {latest_release}")
        print(f"Latest forge: {latest_forge}")

        installed_versions_list = []
        for version in installed_versions:
            installed_versions_list.append(version["id"])
        print(f"Installed versions list: {installed_versions_list}")
        # check in latest release is installed
        if not all((latest_release in installed_versions_list, latest_forge in installed_versions_list)):
            print("Downloading game...")
            self._progress_bar.visible = True
            self._progress_text.visible = True

            self._play_button_disable()
            # self._check_game_button_stop()
            self._check_game_button_disable()
            self.page.update()

            self.download_and_install_minecraft(latest_release)

            self._progress_bar.visible = False
            self._progress_text.visible = False

            self._check_game_button_enable()
            self._play_button_enable()

            if self.page is not None:
                self.page.update()

        else:
            print("Game is already downloaded.")
            options = {
                "username": account.user["user"]["players"][0]["name"],
                "uuid": account.user["user"]["players"][0]["uuid"],
                "token": account.account["access_token"],
            }
            options["jvmArguments"] = [
                f"-javaagent:{MINECRAFT_FOLDER}/authlib-injector.jar=https://auth.cubedvij.pp.ua/authlib-injector"
            ]
            latest_forge = (
                latest_forge.split("-")[0]
                + "-"
                + "forge"
                + "-"
                + latest_forge.split("-")[1]
            )
            minecraft_command = mcl.command.get_minecraft_command(
                latest_forge, MINECRAFT_FOLDER, options
            )
            print(f"Running game: {minecraft_command}")
            self._minecraft_process = subprocess.Popen(minecraft_command)
            self.page.run_task(self._check_minecraft)
            self._play_button_stop()
            self._check_game_button_disable()
            self.page.update()

    def download_and_install_minecraft(self, latest_release):
        mcl.install.install_minecraft_version(
            latest_release, MINECRAFT_FOLDER, self._download_callback
        )

        # install forge
        self._set_progress_text("Встановлення Forge...")
        forge_version = mcl.forge.find_forge_version(latest_release)
        if forge_version is not None:
            mcl.forge.install_forge_version(
                forge_version, MINECRAFT_FOLDER, self._download_callback
            )
            self._set_progress_text("Forge встановлено")
        else:
            self._set_progress_text("Forge не знайдено")

        self._set_progress_text("Встановлення authlib-injector...")

        authlib.download_latest_release(
            f"{MINECRAFT_FOLDER}/authlib-injector.jar",
            self._set_progress,
            self._set_max,
        )

        self._set_progress_text("authlib-injector встановлено")

    def _force_check_game(self, event: ft.TapEvent): ...

    def _stop_game(self, event: ft.TapEvent):
        self._minecraft_process.kill()
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
        self._check_game_button.bgcolor = ft.Colors.PRIMARY_CONTAINER
        self._check_game_button.icon = ft.Icons.RESTART_ALT
        self._check_game_button.on_click = self._force_check_game

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
                self.page.update()
                break
            await asyncio.sleep(3)

    def _set_max(self, max: int):
        self._max_progress = max

    def _open_link(self, link: str):
        if os.name == "nt":
            os.system(f"start {link}")
        else:
            os.system(f"xdg-open {link}")
