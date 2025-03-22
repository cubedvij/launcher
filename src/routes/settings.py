import flet as ft


class SettingsPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/settings")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        title = ft.Text(
            "Налаштування", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE
        )
        back_button = ft.ElevatedButton(
            "Назад", on_click=lambda _: self.page.go("/"), width=300
        )

        self.controls.append(
            ft.Column(
                [title, back_button],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )
