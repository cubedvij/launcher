import flet as ft

from auth import account


class RegisterPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/register")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        title = ft.Text("Реєстрація", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        self.username = ft.TextField(label="Логін", width=300, max_length=16)
        self.password = ft.TextField(label="Пароль", password=True, can_reveal_password=True, width=300, max_length=32)
        self.confirm_password = ft.TextField(label="Підтвердіть пароль", password=True, can_reveal_password=True, width=300, max_length=32)
        
        register_button = ft.ElevatedButton("Зареєструватися", on_click=self.register, width=300)
        back_button = ft.TextButton("Назад", on_click=lambda _: self.page.go("/login"))
        
        self.controls.append(
            ft.Row(
                [
                    ft.Column(
                        [title, self.username, self.password, self.confirm_password, register_button, back_button],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True
            )
        )

    def register(self, e: ft.ControlEvent):
        username = self.username.value.strip()
        password = self.password.value.strip()
        confirm_password = self.confirm_password.value.strip()
        if not all([username, password, confirm_password]):
            snack_bar = ft.SnackBar(ft.Text("Заповніть всі поля!"), bgcolor=ft.Colors.RED_400, open=True)
        elif len(username) < 4:
            snack_bar = ft.SnackBar(ft.Text("Логін повинно містити не менше 4 символів!"), bgcolor=ft.Colors.RED_400, open=True)
        elif len(password) < 8:
            snack_bar = ft.SnackBar(ft.Text("Пароль повинен містити не менше 8 символів!"), bgcolor=ft.Colors.RED_400, open=True)
        elif password != confirm_password:
            snack_bar = ft.SnackBar(ft.Text("Паролі не співпадають!"), bgcolor=ft.Colors.RED_400, open=True)
        else:
            resp = account.register(username, password)
            if resp is True:
                snack_bar = ft.SnackBar(ft.Text("Ви успішно зареєструвались!"), bgcolor=ft.Colors.GREEN_400, open=True)
                self.page.go("/login")
            else:
                snack_bar = ft.SnackBar(ft.Text(resp), bgcolor=ft.Colors.RED_400, open=True)
        e.control.page.overlay.append(snack_bar)
        self.page.update()