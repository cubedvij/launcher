import asyncio
import os
import shutil
import subprocess

import flet as ft

from config import (
    APPDATA_FOLDER,
    LAUNCHER_VERSION,
    RAM_SIZE,
    RAM_STEP,
    LAUNCHER_COLORS,
    LAUNCHER_THEMES,
)
from settings import settings
from utils import Shimmer


class SettingsPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/settings")
        self.page = page
        self.controls = []
        self._click_count = 0
        self._dir_picker = ft.FilePicker(on_result=self._pick_dir_result)
        self._snack_bar = ft.SnackBar(Shimmer(control=ft.Text(), auto_generate=True))
        self._dialog = ft.AlertDialog(
            title="Очистити теку Minecraft?",
            content=ft.Text("Всі файли та папки в теці Minecraft буде видалено."),
            actions=[
                ft.TextButton("Так", on_click=self._clear_minecraft_dir_confirmed),
                ft.TextButton("Ні", on_click=self._dialog_close),
            ],
        )
        self._loading_indicator = ft.Container(
            ft.ProgressRing(
                width=64, height=64, stroke_width=8, visible=True, expand=True
            ),
            alignment=ft.Alignment(0, 0),
            blur=2,
            disabled=True,
            visible=False,
        )
        self.page.overlay.append(self._dir_picker)
        self.page.overlay.append(self._snack_bar)
        self.page.overlay.append(self._dialog)
        self.page.overlay.append(self._loading_indicator)
        self.build_ui()
        # self.page.run_thread(self._meme)

    def build_ui(self):
        self._appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=self.go_index,
                tooltip="На головну",
            ),
            title=ft.Text("Налаштування", size=20),
            leading_width=64,
            center_title=False,
            shape=ft.RoundedRectangleBorder(radius=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self._min_ram_field = ft.TextField(
            value=settings.min_use_ram,
            width=200,
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
            suffix=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                tight=True,
                spacing=16,
                controls=[
                    ft.Text("МБ"),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_UP,
                        on_click=self._increase_min_ram_value,
                    ),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                        on_click=self._decrease_min_ram_value,
                    ),
                ],
            ),
        )

        self._max_ram_field = ft.TextField(
            value=settings.max_use_ram,
            width=200,
            suffix_text="МБ",
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
            border_color=ft.Colors.SECONDARY_CONTAINER,
            suffix=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                tight=True,
                spacing=16,
                controls=[
                    ft.Text("МБ"),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_UP,
                        on_click=self._inscare_max_ram_value,
                    ),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                        on_click=self._decrease_max_ram_value,
                    ),
                ],
            ),
        )
        self._java_args_field = ft.TextField(
            value=" ".join(settings.java_args),
            multiline=True,
            expand=True,
            min_lines=32,
            text_size=14,
            border_color=ft.Colors.SECONDARY_CONTAINER,
        )
        self._card_ram = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Пам'ять", size=16),
                        ft.Divider(height=4),
                        ft.ListTile(
                            title=ft.Text("Мінімальний обсяг виділеної пам'яті:"),
                            trailing=self._min_ram_field,
                        ),
                        ft.ListTile(
                            title=ft.Text("Максимальний обсяг виділеної пам'яті:"),
                            trailing=self._max_ram_field,
                        ),
                    ],
                ),
            ),
        )
        self._card_java_args = ft.Card(
            expand=True,
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Аргументи Java", size=16),
                        ft.Divider(height=4),
                        self._java_args_field,
                    ],
                ),
            ),
        )
        self._is_fullscreen_game = ft.ListTile(
            title=ft.Text("Повноекранний режим:"),
            trailing=ft.Checkbox(value=settings.fullscreen),
        )
        self._game_window_width = ft.ListTile(
            title=ft.Text("Ширина:"),
            trailing=ft.TextField(
                value=settings.window_width,
                width=200,
                input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
                suffix=ft.Text("px"),
            ),
        )
        self._game_window_eight = ft.ListTile(
            title=ft.Text("Висота:"),
            trailing=ft.TextField(
                value=settings.window_height,
                width=200,
                input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
                suffix=ft.Text("px"),
            ),
        )
        self._game_window_settings = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Вікно гри", size=16),
                        ft.Divider(height=4),
                        self._is_fullscreen_game,
                        self._game_window_width,
                        self._game_window_eight,
                    ],
                ),
            ),
        )
        self._minimize_launcher = ft.ListTile(
            title=ft.Text("Мінімізувати лаунчер при запуску гри:"),
            trailing=ft.Checkbox(value=settings.minimize_launcher),
        )
        self._quit_launcher = ft.ListTile(
            title=ft.Text("Закривати лаунчер при запуску гри:"),
            trailing=ft.Checkbox(value=settings.close_launcher),
        )

        self.launcher_theme = ft.ListTile(
            title=ft.Text("Тема лаунчера:"),
            trailing=ft.Dropdown(
                options=[
                    ft.dropdown.Option(
                        color,
                        name
                    )
                    for color, name in LAUNCHER_THEMES.items()
                ],
                value=settings.launcher_theme,
                on_change=self.launcher_theme_change,
                width=200,
            ),
        )
        self.launcher_color = ft.ListTile(
            title=ft.Text("Колір лаунчера:"),
            trailing=ft.Dropdown(
                options=[
                    ft.dropdown.Option(
                        color,
                        name,
                        leading_icon=ft.Icon(ft.Icons.SQUARE_ROUNDED, color=color),
                    )
                    for color, name in LAUNCHER_COLORS.items()
                ],
                value=settings.launcher_color,
                leading_icon=ft.Icon(
                    ft.Icons.SQUARE_ROUNDED,
                    color=settings.launcher_color,
                ),
                on_change=self.launcher_color_change,
                width=200,
            ),
        )
        self._launcher_settings_card = ft.Card(
            expand=True,
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Налаштування лаунчера", size=16),
                        ft.Divider(height=4),
                        self._minimize_launcher,
                        self._quit_launcher,
                        self.launcher_theme,
                        self.launcher_color,
                    ],
                ),
            ),
        )
        # Minecraft directory field
        self._clear_mc_dir_btn = ft.FilledTonalButton(
            text="Очистити теку",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self._clear_minecraft_dir,
            height=40,
            expand=True,
        )
        self._open_mc_dir_btn = ft.FilledTonalButton(
            text="Відкрити теку",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._open_minecraft_dir,
            height=40,
            expand=True,
        )
        self._reset_mc_dir_btn = ft.FilledButton(
            text="Скинути теку",
            icon=ft.Icons.REPLAY,
            on_click=self._reset_minecraft_dir,
            height=40,
            expand=True,
        )
        self._minecraft_dir_field = ft.TextField(
            value=settings.minecraft_directory,
            label="Minecraft",
            border_color=ft.Colors.SECONDARY_CONTAINER,
            expand=True,
            suffix=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                tight=True,
                spacing=16,
                controls=[
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.FOLDER,
                        on_click=self._move_minecraft_dir,
                    ),
                ],
            ),
            read_only=True,
        )
        self._minecraft_dir_card = ft.Card(
            expand=True,
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Тека Minecraft", size=16),
                        ft.Divider(height=4),
                        ft.ListTile(
                            trailing=self._minecraft_dir_field,
                        ),
                        ft.ListTile(
                            leading=ft.Row(
                                spacing=8,
                                controls=[
                                    self._clear_mc_dir_btn,
                                    self._open_mc_dir_btn,
                                    self._reset_mc_dir_btn,
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )
        self._image = ft.Image(
            src="pig.webp",
            width=128,
            height=128,
            fit=ft.ImageFit.CONTAIN,
        )
        self._about_card = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            expand=True,
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                expand=True,
                content=ft.Column(
                    expand=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    controls=[
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "Інфо",
                                    size=16,
                                ),
                                ft.Divider(height=4),
                                ft.Button(
                                    content=self._image,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        padding=ft.Padding(0, 0, 0, 0),
                                        shadow_color=ft.Colors.TRANSPARENT,
                                        overlay_color=ft.Colors.TRANSPARENT,
                                        mouse_cursor=ft.MouseCursor.PRECISE,
                                    ),
                                    on_click=self._count_clicks,
                                ),
                                ft.Text(
                                    f"{LAUNCHER_VERSION}\n"
                                    f"Автор: hampta\n"
                                    f"Ліцензія: GPL-3.0\n",
                                    text_align=ft.TextAlign.CENTER,
                                    size=16,
                                ),
                                ft.Text(
                                    "Окрема подяка: \n"
                                    "rflmm, Vanchak(BAHRT), Михайло Слюсар, DTen_, sobleron, NekMakarov, arisu",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "This launcher is not affiliated with Mojang. All rights to Minecraft belong to Mojang.\n"
                                    "Minecraft is a trademark of Mojang AB. © 2009-2025 Mojang AB. All rights reserved.\n\n"
                                    "CubeDvij Launcher © 2025 hampta. All rights reserved.",
                                    size=12,
                                    text_align=ft.TextAlign.END,
                                    expand=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        )

        # self._text_span1 = ft.TextSpan(
        #     "",
        #     ft.TextStyle(
        #         size=18,
        #         weight=ft.FontWeight.NORMAL,
        #         foreground=ft.Paint(
        #             color=ft.Colors.BLACK,
        #             stroke_width=2,
        #             style=ft.PaintingStyle.STROKE,
        #         ),
        #     ),
        # )

        # self._text_span2 = ft.TextSpan(
        #     "",
        #     ft.TextStyle(
        #         size=18,
        #         weight=ft.FontWeight.NORMAL,
        #         color=ft.Colors.WHITE,
        #         shadow=ft.BoxShadow(
        #             color=ft.Colors.BLACK,
        #             spread_radius=0,
        #             offset=ft.Offset(2, 2),
        #         ),
        #     ),
        # )

        # self._text = ft.Stack(
        #     [
        #         ft.Text(
        #             spans=[self._text_span1],
        #             text_align=ft.TextAlign.CENTER,
        #         ),
        #         ft.Text(
        #             spans=[self._text_span2],
        #             text_align=ft.TextAlign.CENTER,
        #         ),
        #     ],
        #     alignment=ft.Alignment(0, 0),
        #     fit=ft.StackFit.LOOSE,
        #     expand=True,
        #     expand_loose=True,
        # )
        # self.nigger = ft.Column(
        #     controls=[self._text],
        #     scroll=ft.ScrollMode.HIDDEN,
        # )
        # self._prikol = ft.Stack(
        #     [
        #         ft.Container(
        #             content=ft.Image(src="/home/hampta/Downloads/caterpillar.gif", fit=ft.ImageFit.FILL),
        #             padding=ft.Padding(0, 0, 0, 0),
        #         ),
        #         ft.Container(alignment=ft.Alignment(0, 0), content=self.nigger),
        #     ],
        #     fit=ft.StackFit.EXPAND,
        # )

        self._java_settings_tab = ft.Tab(
            icon=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CODE),
                    ft.Text("Java"),
                ]
            ),
            content=ft.Column(
                spacing=4,
                controls=[self._card_ram, self._card_java_args],
            ),
        )
        self._game_settings_tab = ft.Tab(
            icon=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.VIDEOGAME_ASSET_OUTLINED),
                    ft.Text("Гра"),
                ]
            ),
            content=ft.Column(
                spacing=4,
                controls=[
                    self._game_window_settings,
                    self._minecraft_dir_card,
                ],
            ),
        )
        self._launcher_settings_tab = ft.Tab(
            icon=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS),
                    ft.Text("Лаунчер"),
                ]
            ),
            content=ft.Column(
                spacing=4,
                controls=[self._launcher_settings_card],
            ),
        )
        self._about_tab = ft.Tab(
            icon=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO),
                    ft.Text("Про програму"),
                ]
            ),
            content=ft.Column(
                spacing=4,
                controls=[
                    self._about_card,
                ],
            ),
        )
        # self._game_logs_tab = ft.Tab(
        #     text="Логи",
        #     content=ft.Column(
        #         spacing=4,
        #         controls=[self._logs_card],
        #     ),
        # )
        self._tabs = ft.Tabs(
            animation_duration=300,
            expand=True,
            scrollable=True,
            tabs=[
                self._java_settings_tab,
                self._game_settings_tab,
                self._launcher_settings_tab,
                self._about_tab,
                # self._game_logs_tab,
            ],
        )
        self.pagelet = ft.Pagelet(
            expand=True,
            appbar=self._appbar,
            content=ft.Container(
                content=self._tabs,
                border_radius=8,
            ),
        )
        self.controls.append(self.pagelet)
        self.page.update()

    # def _add_text_to_logs(self, event):
    #     logging.info("Add text")
    #     self._logs_text_field.value += "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam eget nunc nec nunc ultricies ultricies. Nullam nec nunc nec nunc ultricies ultricies. Nullam nec nunc nec nunc ultricies ultricies.\n"
    #     self.page.update()

    # def _meme(self):
    #     time.sleep(2)
    #     ip_info = httpx.get("https://ipapi.co/json/").json()
    #     # format ip_info to multiline string
    #     ip_info_str = "\n".join(
    #         [
    #             f"{key.replace('_', ' ').upper()}: {value}"
    #             for key, value in ip_info.items()
    #         ]
    #     )
    #     for char in ip_info_str:
    #         self._text_span1.text += char
    #         self._text_span2.text += char
    #         self.nigger.scroll_to(offset=-1)
    #         time.sleep(0.03)
    #         self.page.update()

    async def _count_clicks(self, event):
        self._click_count += 1
        if self._click_count == 10:
            self._show_snack_bar("Шоти клікаешь!", ft.Colors.YELLOW_200)
        if self._click_count == 20:
            self._show_snack_bar("Пиздець, ти що, дебіл?", ft.Colors.YELLOW_400)
        if self._click_count == 30:
            self._show_snack_bar("Ти точно здоровий на голову?", ft.Colors.ORANGE_200)
        if self._click_count == 40:
            self._show_snack_bar("Ти походу йобу дав", ft.Colors.ORANGE_400)
        if self._click_count == 50:
            self._show_snack_bar("Я зйобую", ft.Colors.RED_400)
            for i in range(512):
                self._image.offset = ft.Offset(i / 60, 0)
                self._image.update()
                await asyncio.sleep(0.01)
            for i in range(-512, 1):
                self._image.offset = ft.Offset(i / 60, 0)
                self._image.update()
                await asyncio.sleep(0.01)
        if self._click_count == 100:
            self._image_2 = ft.Image(
                src="https://hfs.hampta.pp.ua/[Memes]/poshalko.webp",
                width=self.page.window.width,
                height=self.page.window.height,
                fit=ft.ImageFit.FILL,
            )

            self.page.overlay.append(
                ft.Container(
                    content=self._image_2,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, 0, 0, 0),
                    margin=ft.Margin(0, 0, 0, 0),
                    width=self.page.window.width,
                    height=self.page.window.height,
                    bgcolor=ft.Colors.TRANSPARENT,
                )
            )
            self.page.update()
            await asyncio.sleep(3.63)
            self.page.overlay.pop()
            self.page.update()

    def _increase_min_ram_value(self, event):
        value = int(self._min_ram_field.value)
        if value + RAM_STEP > self._max_ram_field.value:
            return
        self._min_ram_field.value = value + RAM_STEP
        self.page.update()

    def _decrease_min_ram_value(self, event):
        value = int(self._min_ram_field.value)
        if value - RAM_STEP < RAM_STEP:
            return
        self._min_ram_field.value = value - RAM_STEP
        self.page.update()

    def _inscare_max_ram_value(self, event):
        value = int(self._max_ram_field.value)
        if value + RAM_STEP > RAM_SIZE:
            return
        self._max_ram_field.value = value + RAM_STEP
        self.page.update()

    def _decrease_max_ram_value(self, event):
        value = int(self._max_ram_field.value)
        if value - RAM_STEP < self._min_ram_field.value:
            return
        self._max_ram_field.value = value - RAM_STEP
        self.page.update()

    def _dialog_close(self, event):
        self._dialog.open = False
        self.page.update()

    def _move_minecraft_dir(self, event):
        self._dir_picker.get_directory_path()

    def _pick_dir_result(self, e: ft.FilePickerResultEvent):
        if not e.path or e.path == settings.minecraft_directory:
            return
        try:
            self._loading_indicator.visible = True
            self._loading_indicator.disabled = False
            self.page.update()

            if not os.path.exists(e.path):
                os.makedirs(e.path)
            for filename in os.listdir(settings.minecraft_directory):
                src = os.path.join(settings.minecraft_directory, filename)
                dst = os.path.join(e.path, filename)
                if os.path.exists(dst):
                    if os.path.isfile(dst) or os.path.islink(dst):
                        os.unlink(dst)
                    elif os.path.isdir(dst):
                        shutil.rmtree(dst)
                shutil.move(src, e.path)
            settings.minecraft_directory = e.path
            self._minecraft_dir_field.value = e.path
            settings.save()
            self._show_snack_bar("Теку успішно переміщено!", ft.Colors.GREEN_400)
        except Exception as ex:
            self._show_snack_bar(f"Помилка: {ex}", ft.Colors.RED_400)
        finally:
            self._dir_picker.path = None
            self._loading_indicator.visible = False
            self._loading_indicator.disabled = True
            self._dir_picker.update()
            self.page.update()

    def _clear_minecraft_dir(self, event):
        self._dialog.open = True
        self.page.update()

    def _clear_minecraft_dir_confirmed(self, event):
        self._dialog.open = False
        self.page.update()
        self._loading_indicator.visible = True
        self._loading_indicator.disabled = False
        self.page.update()
        mc_dir = settings.minecraft_directory
        try:
            for filename in os.listdir(mc_dir):
                path = os.path.join(mc_dir, filename)
                if os.path.isfile(path) or os.path.islink(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            self._show_snack_bar("Теку очищено!", ft.Colors.GREEN_400)
        except Exception as e:
            self._show_snack_bar(f"Помилка: {e}", ft.Colors.RED_400)
        finally:
            self._loading_indicator.visible = False
            self._loading_indicator.disabled = True
            self.page.update()

    def _open_minecraft_dir(self, event):
        mc_dir = settings.minecraft_directory
        try:
            if os.name == "nt":
                os.startfile(mc_dir)
            elif os.name == "posix":
                subprocess.Popen(["xdg-open", mc_dir])
            else:
                raise Exception("Невідома ОС")
        except Exception as e:
            self._show_snack_bar(f"Помилка: {e}", ft.Colors.RED_400)

    def _reset_minecraft_dir(self, event):
        default_path = os.path.join(APPDATA_FOLDER, ".minecraft")
        try:
            if not os.path.exists(default_path):
                os.makedirs(default_path)
            settings.minecraft_directory = default_path
            self._minecraft_dir_field.value = default_path
            settings.save()
            self._show_snack_bar("Теку скинуто!", ft.Colors.GREEN_400)
        except Exception as e:
            self._show_snack_bar(f"Помилка: {e}", ft.Colors.RED_400)

    def _show_snack_bar(self, message, color):
        self._snack_bar.content = ft.Text(message)
        self._snack_bar.bgcolor = color
        self._snack_bar.open = True
        self.page.update()

    def launcher_theme_change(self, event):
        settings.launcher_theme = event.data
        settings.save()
        self.page.theme_mode = event.data
        self.page.update()
        
    def launcher_color_change(self, event):
        settings.launcher_color = event.data
        settings.save()
        self.page.theme.color_scheme_seed = event.data
        self.launcher_color.trailing.leading_icon.color = event.data
        self.page.update()

    def go_index(self, event):
        settings.min_use_ram = int(self._min_ram_field.value)
        settings.max_use_ram = int(self._max_ram_field.value)
        settings.java_args = self._java_args_field.value.split(" ")
        settings.fullscreen = self._is_fullscreen_game.trailing.value
        settings.window_width = int(self._game_window_width.trailing.value)
        settings.window_height = int(self._game_window_eight.trailing.value)
        settings.minimize_launcher = self._minimize_launcher.trailing.value
        settings.close_launcher = self._quit_launcher.trailing.value
        settings.minecraft_directory = self._minecraft_dir_field.value
        settings.save()
        self.page.go("/")
