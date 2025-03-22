import base64
import flet as ft

from ..auth import account
from ..config import SKINS_CACHE_FOLDER


class ProfilePage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/profile")
        self.page = page
        self.controls = []
        self.build_ui()

    async def update_user_info(self, event: ft.RouteChangeEvent):
        await account.render_skin()
        self._list_tile.title.value = account.user["user"]["players"][0]["name"]
        self._list_tile.subtitle.value = account.user["user"]["players"][0]["uuid"]
        self._skin_types.value = account.user["user"]["players"][0]["skinModel"]
        self.update_skin()
        event.page.update()

    def build_ui(self):
        self._skin_file_picker = ft.FilePicker(on_result=self.on_upload_skin)
        self._cape_file_picker = ft.FilePicker(on_result=self.on_upload_cape)
        self._alert_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Підтвердження"),
            content=ft.Text("Ви впевнені, що хочете вийти?"),
            actions=[
                ft.TextButton("Так", on_click=lambda e: self.logout()),
                ft.TextButton("Ні", on_click=self.close_alert),
            ],
        )
        self._snack_bar = ft.SnackBar(ft.Text("..."))
        self._appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                on_click=self.go_index,
                tooltip="На головну",
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    on_click=self.open_alert,
                    tooltip="Вийти з аккаунта",
                ),
            ],
            title=ft.Text("Профіль", size=20),
            leading_width=64,
            center_title=False,
            shape=ft.RoundedRectangleBorder(radius=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        self._list_tile = ft.ListTile(
            leading=ft.Image(
                src=f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-face.png",
                width=64,
                height=64,
                fit=ft.ImageFit.CONTAIN,
            ),
            title=ft.TextField(
                # account.user["user"]["players"][0]["name"],
                "...",
                hint_text="Ім'я користувача",
                disabled=True,
                # text_align=ft.TextAlign.CENTER,
                text_vertical_align=ft.VerticalAlignment.START,
                border=ft.InputBorder.UNDERLINE,
                filled=True,
                on_submit=self._save_nickname
            ),
            subtitle=ft.Text(
                # account.user["user"]["players"][0]["uuid"],
                "...",
                size=10,
                selectable=True,
            ),
            trailing=ft.FloatingActionButton(
                icon=ft.Icons.EDIT,
                tooltip="Редагувати",
                mini=True,
                width=32,
                height=32,
                on_click=self._edit_nickname,
            ),
            title_alignment=ft.ListTileTitleAlignment.TITLE_HEIGHT,
            content_padding=ft.Padding(8, 2, 8, 2),
        )

        self._skin_types = ft.RadioGroup(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Тип скіна:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Radio(value="classic", label="Класичний"),
                            ft.Radio(value="slim", label="Тонкий"),
                        ],
                    ),
                ],
            ),
            on_change=self.on_skin_type_change,
        )
        # set default skin type
        # self._skin_types.value = account.user["user"]["players"][0]["skinModel"]
        self._skin_settings = ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.FilledTonalButton(
                    "Завантажити скін",
                    icon=ft.Icons.FACE,
                    expand=True,
                    on_click=lambda e: self._skin_file_picker.pick_files(
                        dialog_title="Виберіть файл скіна",
                        allowed_extensions=["png"],
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.WHITE,
                    scale=0.8,
                    bgcolor=ft.Colors.RED_400,
                    tooltip="Видалити скін",
                    on_click=self.on_delete_skin,
                ),
            ],
        )
        self._cape_settings = ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.FilledTonalButton(
                    "Завантажити плащ",
                    icon=ft.Icons.BOOKMARK,
                    expand=True,
                    on_click=lambda e: self._cape_file_picker.pick_files(
                        dialog_title="Виберіть файл плаща",
                        allowed_extensions=["png"],
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.WHITE,
                    scale=0.8,
                    bgcolor=ft.Colors.RED_400,
                    tooltip="Видалити плащ",
                    on_click=self.on_delete_cape,
                ),
            ],
        )
        self._new_password = ft.TextField(
            label="Новий Пароль",
            password=True,
            can_reveal_password=True,
            max_length=32,
        )
        self._confirm_password = ft.TextField(
            label="Підтвердіть Пароль",
            password=True,
            can_reveal_password=True,
            max_length=32,
        )
        self._change_password = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                self._new_password,
                self._confirm_password,
                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.FilledTonalButton(
                            "Змінити пароль",
                            icon=ft.Icons.LOCK,
                            expand=True,
                            on_click=self.on_change_password,
                        ),
                    ],
                ),
            ],
        )
        self._card = ft.Card(
            expand=True,
            content=ft.Container(
                padding=ft.Padding(8, 0, 8, 0),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    expand=True,
                    controls=[
                        self._list_tile,
                        ft.Divider(),
                        self._skin_types,
                        self._skin_settings,
                        self._cape_settings,
                        ft.Divider(),
                        # change password
                        ft.Text(
                            "Зміна пароля",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        self._change_password,
                    ],
                ),
            ),
        )
        self._skin_image = ft.Image(
            # src=f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-skin.png",
            src=None,
            width=216,
            height=392
        )
        self._skin_back_image = ft.Image(
            # src=f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-back.png",
            src=None,
            width=216,
            height=392
        )

        self.pagelet = ft.Pagelet(
            expand=True,
            appbar=self._appbar,
            content=ft.Row(
                expand=True,
                controls=[
                    self._card,
                    ft.Card(
                        content=ft.Row(
                            width=500,
                            controls=[
                                ft.Container(
                                    padding=ft.Padding(16, 0, 16, 0),
                                    content=self._skin_image,
                                    expand=True,
                                ),
                                ft.VerticalDivider(),
                                ft.Container(
                                    padding=ft.Padding(16, 0, 16, 0),
                                    content=self._skin_back_image,
                                    expand=True,
                                ),
                            ],
                        ),
                    ),
                    # ft.VerticalDivider(),
                    # self._skin_back_image,
                ],
            ),
            # height=200,
        )
        self.controls.append(self.pagelet)
        self.page.overlay.append(self._skin_file_picker)
        self.page.overlay.append(self._cape_file_picker)
        self.page.update()

    def _edit_nickname(self, e: ft.ControlEvent):
        e.control.parent.title.disabled = False
        e.control.parent.trailing.icon = ft.Icons.SAVE
        e.control.parent.trailing.tooltip = "Зберегти"
        e.control.parent.trailing.on_click = self._save_nickname
        e.control.update()
        e.control.parent.title.focus()

    def _save_nickname(self, e: ft.ControlEvent):
        if account.is_valid_nickname(e.control.parent.title.value):
            resp = account.update_player({"name": e.control.parent.title.value})
            resp_json = resp.json()
            if resp.status_code == 200:
                if resp_json["name"] == e.control.parent.title.value:
                    account.get_user()
                    e.control.parent.title.disabled = True
                    e.control.parent.trailing.icon = ft.Icons.EDIT
                    e.control.parent.trailing.tooltip = "Редагувати"
                    e.control.parent.trailing.on_click = self._edit_nickname
                    self._snack_bar.content = ft.Text(
                        "Ім'я користувача успішно змінено!"
                    )
                    self._snack_bar.bgcolor = ft.Colors.GREEN_400
                    account.update_skin = True
            else:
                self._snack_bar.content = ft.Text(resp_json["message"])
                self._snack_bar.bgcolor = ft.Colors.RED_400
        else:
            self._snack_bar.content = ft.Text("Недійсне ім'я користувача!")
            self._snack_bar.bgcolor = ft.Colors.RED_400
        self.page.open(self._snack_bar)
        self.page.update()
        return

    def update_skin(self):
        self._list_tile.leading.src = (
            f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-face.png"
        )
        self._skin_image.src = f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-skin.png"
        self._skin_back_image.src = f"{SKINS_CACHE_FOLDER}/{account.skin_hash}-back.png"

    async def on_upload_skin(self, e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            # convert image to base64
            with open(file_path, "rb") as file:
                img = base64.b64encode(file.read()).decode("utf-8")
            # update skin
            resp = account.update_player({"skinBase64": img})
            resp_json = resp.json()
            if resp.status_code == 200:
                if resp_json["skinUrl"]:
                    account.update_skin = True
                    await account.render_skin()
                    self.update_skin()
                    self._snack_bar.content = ft.Text("Скін успішно змінено!")
                    self._snack_bar.bgcolor = ft.Colors.GREEN_400
            else:
                self._snack_bar.content = ft.Text(resp_json["message"])
                self._snack_bar.bgcolor = ft.Colors.RED_400
            self.page.open(self._snack_bar)
            self.page.update()
        return

    async def on_upload_cape(self, e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            # convert image to base64
            with open(file_path, "rb") as file:
                img = base64.b64encode(file.read()).decode("utf-8")
            # update cape
            resp = account.update_player({"capeBase64": img})
            resp_json = resp.json()
            if resp.status_code == 200:
                if resp_json["capeUrl"]:
                    account.update_skin = True
                    await account.render_skin()
                    self.update_skin()
                    self._snack_bar.content = ft.Text("Плащ успішно змінено!")
                    self._snack_bar.bgcolor = ft.Colors.GREEN_400
            else:
                self._snack_bar.content = ft.Text(resp_json["message"])
                self._snack_bar.bgcolor = ft.Colors.RED_400
            self.page.open(self._snack_bar)
            self.page.update()
        return

    async def on_delete_skin(self, e):
        resp = account.update_player({"deleteSkin": True})
        resp_json = resp.json()
        if resp.status_code == 200:
            if resp_json["skinUrl"] is None:
                account.update_skin = True
                await account.render_skin()
                self.update_skin()
                self._snack_bar.content = ft.Text("Скін успішно видалено!")
                self._snack_bar.bgcolor = ft.Colors.YELLOW_400
        else:
            self._snack_bar.content = ft.Text(resp_json["message"])
            self._snack_bar.bgcolor = ft.Colors.RED_400
        self.page.open(self._snack_bar)
        self.page.update()

    async def on_delete_cape(self, e):
        resp = account.update_player({"deleteCape": True})
        resp_json = resp.json()
        if resp.status_code == 200:
            if resp_json["capeUrl"] is None:
                account.update_skin = True
                await account.render_skin()
                self.update_skin()
                self._snack_bar.content = ft.Text("Плащ успішно видалено!")
                self._snack_bar.bgcolor = ft.Colors.YELLOW_400
        else:
            self._snack_bar.content = ft.Text(resp_json["message"])
            self._snack_bar.bgcolor = ft.Colors.RED_400
        self.page.open(self._snack_bar)
        self.page.update()

    def on_skin_type_change(self, e):
        resp = account.update_player({"skinModel": e.data})
        resp_json = resp.json()
        if resp.status_code == 200:
            if resp_json["skinModel"] == e.data:
                account.get_user()
                account.update_skin = True
                self.update_skin()
                self._snack_bar.content = ft.Text("Тип скіна успішно змінено!")
                self._snack_bar.bgcolor = ft.Colors.GREEN_400
        else:
            self._snack_bar.content = ft.Text(resp_json["message"])
            self._snack_bar.bgcolor = ft.Colors.RED_400
        self.page.open(self._snack_bar)
        self.page.update()

    def on_change_password(self, e):
        new_password = self._new_password.value.strip()
        confirm_password = self._confirm_password.value.strip()
        if not all([new_password, confirm_password]):
            self._snack_bar.content = ft.Text("Заповніть всі поля!")
            self._snack_bar.bgcolor = ft.Colors.RED_400
        elif len(new_password) < 8:
            self._snack_bar.content = ft.Text(
                "Пароль повинен містити не менше 8 символів!"
            )
            self._snack_bar.bgcolor = ft.Colors.RED_400
        elif new_password != confirm_password:
            self._snack_bar.content = ft.Text("Паролі не співпадають!")
            self._snack_bar.bgcolor = ft.Colors.RED_400
        else:
            resp = account.update_user({"password": new_password})
            resp_json = resp.json()
            if resp.status_code == 200:
                self._snack_bar.content = ft.Text("Пароль успішно змінено!")
                self._snack_bar.bgcolor = ft.Colors.GREEN_400
            else:
                self._snack_bar.content = ft.Text(resp_json["message"])
                self._snack_bar.bgcolor = ft.Colors.RED_400
        self.page.open(self._snack_bar)
        self.page.update()

    def go_index(self, e):
        self._list_tile.title.disabled = True
        self._list_tile.trailing.icon = ft.Icons.EDIT
        self._list_tile.trailing.on_click = self._edit_nickname
        self._new_password.value = ""
        self._confirm_password.value = ""
        self.page.update()
        self.page.go("/")

    def logout(self):
        account.logout()
        self.page.go("/login")

    def open_alert(self, e):
        e.control.page.overlay.append(self._alert_dialog)
        self._alert_dialog.open = True
        e.control.page.update()

    def close_alert(self, e):
        self.page.close(self._alert_dialog)
        self.page.update()
