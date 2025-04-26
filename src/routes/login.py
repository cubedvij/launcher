import flet as ft

from src.auth import account


class LoginPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/login")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        title = ft.Text(
            "Авторизуватися", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE
        )

        self.username = ft.TextField(
            label="Логін", autofocus=True, width=300, on_submit=self.login
        )
        self.password = ft.TextField(
            label="Пароль", password=True, can_reveal_password=True, width=300, on_submit=self.login
        )

        login_button = ft.ElevatedButton("Увійти", on_click=self.login, width=300)

        register_button = ft.TextButton(
            "Реєстрація", on_click=lambda _: self.page.go("/register"), width=300
        )

        self.controls.append(
            ft.Row(
                [
                    ft.Column(
                        [
                            title,
                            self.username,
                            self.password,
                            login_button,
                            register_button,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        )

    def login(self, e):
        username = self.username.value.strip()
        password = self.password.value.strip()
        if username and password:
            response = account.login(username, password)
            if response.status_code != 200:
                status_bar = ft.SnackBar(
                    ft.Text(response.json()["errorMessage"]), open=True, bgcolor=ft.colors.RED_400
                )
            else:
                status_bar = ft.SnackBar(
                    ft.Text("Успішно авторизовано!"),
                    open=True,
                    bgcolor=ft.colors.GREEN_400,
                )

                self.page.go("/")
        else:
            status_bar = ft.SnackBar(
                ft.Text("Заповніть всі поля!"), open=True, bgcolor=ft.colors.RED_400
            )
        e.control.page.overlay.append(status_bar)
        self.page.update()
