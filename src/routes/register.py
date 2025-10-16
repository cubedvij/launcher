import flet as ft

from auth import account
from config import RULES_URL


class RegisterPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/register")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        title = ft.Text("Реєстрація", size=24, weight=ft.FontWeight.BOLD)

        self.username = ft.TextField(
            label="Логін", width=300, max_length=16, autofocus=True
        )
        self.password = ft.TextField(
            label="Пароль",
            password=True,
            can_reveal_password=True,
            width=300,
            max_length=32,
        )
        self.confirm_password = ft.TextField(
            label="Підтвердіть пароль",
            password=True,
            can_reveal_password=True,
            width=300,
            max_length=32,
        )

        register_button = ft.ElevatedButton(
            "Зареєструватися",
            icon=ft.Icons.PERSON_ADD_ALT,
            on_click=self.register,
            width=300,
        )
        back_button = ft.TextButton(
            "Назад",
            icon=ft.Icons.ARROW_BACK,
            width=300,
            on_click=lambda e: self.page.go("/login"),
        )
        rules_agreement_text = ft.Text(
            disabled=False,
            spans=[
                ft.TextSpan(
                    "Я погоджуюсь з ",
                ),
                ft.TextSpan(
                    "правилами сервера",
                    ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                    url=RULES_URL,
                    on_enter=self.highlight_link,
                    on_exit=self.unhighlight_link,
                ),
            ],
        )
        self.rules_agreement = ft.Checkbox(
            label=rules_agreement_text,
            value=False,
        )

        self.controls.append(
            ft.Row(
                [
                    ft.Column(
                        [
                            title,
                            self.username,
                            self.password,
                            self.confirm_password,
                            self.rules_agreement,
                            register_button,
                            back_button,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        )

    def register(self, e: ft.ControlEvent):
        if self.rules_agreement.value is False:
            snack_bar = ft.SnackBar(
                ft.Text("Ви повинні погодитись з правилами!"),
                bgcolor=ft.Colors.ERROR,
                open=True,
            )
            self.rules_agreement.is_error = True
            e.control.page.overlay.append(snack_bar)
            self.page.update()
            return
        username = self.username.value.strip()
        password = self.password.value.strip()
        confirm_password = self.confirm_password.value.strip()
        if not all([username, password, confirm_password]):
            snack_bar = ft.SnackBar(
                ft.Text("Заповніть всі поля!"), bgcolor=ft.Colors.ERROR, open=True
            )
        elif len(username) < 4:
            snack_bar = ft.SnackBar(
                ft.Text("Логін повинен містити не менше 4 символів!"),
                bgcolor=ft.Colors.ERROR,
                open=True,
            )
        elif len(password) < 8:
            snack_bar = ft.SnackBar(
                ft.Text("Пароль повинен містити не менше 8 символів!"),
                bgcolor=ft.Colors.ERROR,
                open=True,
            )
        elif password != confirm_password:
            snack_bar = ft.SnackBar(
                ft.Text("Паролі не співпадають!"), bgcolor=ft.Colors.ERROR, open=True
            )
        else:
            resp = account.register(username, password)
            if resp is True:
                snack_bar = ft.SnackBar(
                    ft.Text("Ви успішно зареєструвались!"),
                    bgcolor=ft.Colors.GREEN_400,
                    open=True,
                )
                self.page.go("/login")
            else:
                snack_bar = ft.SnackBar(
                    ft.Text(resp), bgcolor=ft.Colors.ERROR, open=True
                )
        e.control.page.overlay.append(snack_bar)
        self.page.update()

    def highlight_link(self, e):
        e.control.style.color = ft.Colors.BLUE
        e.control.update()

    def unhighlight_link(self, e):
        e.control.style.color = None
        e.control.update()
