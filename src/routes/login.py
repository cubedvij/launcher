import flet as ft

from auth import account


class LoginPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/login")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        title = ft.Text(
            "Авторизуватися",
            size=24,
            weight=ft.FontWeight.BOLD,
        )

        self.username = ft.TextField(
            label="Логін", autofocus=True, width=300, on_submit=self.login
        )
        self.password = ft.TextField(
            label="Пароль",
            password=True,
            can_reveal_password=True,
            width=300,
            on_submit=self.login,
        )

        login_button = ft.ElevatedButton(
            "Увійти",
            icon=ft.Icons.LOGIN_OUTLINED,
            width=300,
            on_click=self.login,
        )

        register_button = ft.TextButton(
            "Реєстрація",
            icon=ft.Icons.EDIT_OUTLINED,
            width=300,
            on_click=self.register,
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

    def register(self, e):
        self.username.value = ""
        self.password.value = ""
        self.page.go("/register")

    def login(self, e):
        username = self.username.value.strip()
        password = self.password.value.strip()
        if username and password:
            response = account.login(username, password)
            if response.status_code != 200:
                self._status_bar = ft.SnackBar(
                    ft.Text(response.json()["message"]),
                    bgcolor=ft.Colors.RED_400,
                    behavior=ft.SnackBarBehavior.FLOATING,
                )
            else:
                self._status_bar = ft.SnackBar(
                    ft.Text("Успішно авторизовано!"),
                    bgcolor=ft.Colors.GREEN_400,
                    behavior=ft.SnackBarBehavior.FLOATING,
                    duration=250,
                )
                # Clear the input fields after successful login
                self.username.value = ""
                self.password.value = ""
                # Redirect to the home page after successful login
                self.page.go("/")
        else:
            self._status_bar = ft.SnackBar(
                ft.Text("Заповніть всі поля!"),
                bgcolor=ft.Colors.RED_400,
                behavior=ft.SnackBarBehavior.FLOATING,
            )
        self.page.open(self._status_bar)
        # Clear the input fields after login attempt
        self.page.update()
