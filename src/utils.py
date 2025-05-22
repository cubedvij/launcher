import asyncio
import logging

import flet as ft


# flet-contrib
class Shimmer(ft.Container):
    def __init__(
        self,
        ref=None,
        control=None,
        color=None,
        color1=None,
        color2=None,
        height=None,
        width=None,
        auto_generate: bool = False,
    ) -> None:
        super().__init__()

        self.color = color
        self.color1 = color1
        self.color2 = color2
        self.height = height
        self.width = width

        if ref is None:
            self.ref = ft.Ref[ft.ShaderMask]()
        else:
            self.ref = ref

        if self.color1 is None and self.color2 is None and self.color is None:
            self.__color1 = ft.Colors.SURFACE
            self.__color2 = ft.Colors.with_opacity(0.5, ft.Colors.SURFACE)
        elif self.color is not None:
            self.__color1 = self.color
            self.__color2 = ft.Colors.with_opacity(0.5, self.color)
        elif self.color1 is not None and self.color2 is not None:
            self.__color1 = self.color1
            self.__color2 = ft.Colors.with_opacity(0.5, self.color2)
        if auto_generate:
            self.control = self.create_dummy(control)
        else:
            self.control = control

        self.__stop_shine = False

        self.i = -0.1
        self.gap = 0.075

    def build(self):
        gradient = ft.LinearGradient(
            colors=[self.__color2, self.__color1, self.__color2],
            stops=[
                0 + self.i - self.gap,
                self.i,
                self.gap + self.i,
            ],
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
        )

        self.__shadermask = ft.ShaderMask(
            ref=self.ref,
            content=self.control,
            blend_mode=ft.BlendMode.DST_IN,
            height=self.height,
            width=self.width,
            shader=gradient,
        )

        self.content = self.__shadermask
        self.bgcolor = self.__color1

    async def shine_async(self):
        try:
            while self.i <= 5:
                gradient = ft.LinearGradient(
                    colors=[self.__color2, self.__color1, self.__color2],
                    stops=[
                        0 + self.i - self.gap,
                        self.i,
                        self.gap + self.i,
                    ],
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                )
                self.ref.current.shader = gradient
                self.ref.current.update()
                self.i += 0.02
                if self.i >= 1.1:
                    self.i = -0.1
                    await asyncio.sleep(0.4)
                await asyncio.sleep(0.01)
        except Exception as e:
            logging.error("EXCEPTION", e)

    def create_dummy(self, target=None):
        opacity = 0.1
        color = ft.Colors.ON_PRIMARY_CONTAINER

        def circle(size=60):
            return ft.Container(
                height=size,
                width=size,
                bgcolor=ft.Colors.with_opacity(opacity, color),
                border_radius=size,
            )

        def rectangle(height, content=None):
            return ft.Container(
                content=content,
                height=height,
                width=height * 2.5,
                bgcolor=ft.Colors.with_opacity(opacity, color),
                border_radius=20,
                alignment=ft.alignment.bottom_center,
                padding=20,
            )

        def tube(width):
            return ft.Container(
                height=10,
                width=width,
                bgcolor=ft.Colors.with_opacity(opacity, color),
                border_radius=20,
                expand=0,
            )

        if target is None:
            target = self.control
        controls, content, title, subtitle, leading, trailing = (
            False,
            False,
            False,
            False,
            False,
            False,
        )
        ctrl_name = target._get_control_name()
        for key in list(ft.__dict__.keys())[::-1]:
            if key.lower() == ctrl_name and key != ctrl_name:
                dummy = ft.__dict__[key]()

        if ctrl_name in ["text"] and target.data == "shimmer_load":
            dummy = tube(len(target.__dict__["_Control__attrs"]["value"][0]) * 7.5)
        elif ctrl_name in ["textbutton"] and target.data == "shimmer_load":
            dummy = rectangle(40)
        elif ctrl_name in ["icon"] and target.data == "shimmer_load":
            dummy = circle(30)
        elif ctrl_name in ["image"] and target.data == "shimmer_load":
            dummy = ft.Container(
                bgcolor=ft.Colors.with_opacity(opacity, color), expand=True
            )
        elif ctrl_name in ["image"]:
            dummy = ft.Container(expand=True)

        for key in list(target.__dict__.keys())[::-1]:
            if (
                key.lower().split("__")[-1] == "controls"
                and target.__dict__[key] is not None
            ):
                controls = True
            elif (
                key.lower().split("__")[-1] == "content"
                and target.__dict__[key] is not None
            ):
                content = True
            elif (
                key.lower().split("__")[-1] == "title"
                and target.__dict__[key] is not None
            ):
                title = True
            elif (
                key.lower().split("__")[-1] == "subtitle"
                and target.__dict__[key] is not None
            ):
                subtitle = True
            elif (
                key.lower().split("__")[-1] == "leading"
                and target.__dict__[key] is not None
            ):
                leading = True
            elif (
                key.lower().split("__")[-1] == "trailing"
                and target.__dict__[key] is not None
            ):
                trailing = True

        ctrl_attrs = target.__dict__["_Control__attrs"]
        if ctrl_attrs is not None:
            for each_pos in ctrl_attrs.keys():
                if each_pos not in [
                    "text",
                    "value",
                    "label",
                    "foregroundimageurl",
                    "bgcolor",
                    "name",
                    "color",
                    "icon",
                    "src",
                    "src_base64",
                ]:
                    try:
                        dummy._set_attr(each_pos, ctrl_attrs[each_pos][0])
                    except Exception as e:
                        logging.error("EXCEPTION", e, ctrl_name, each_pos)

        for each_pos in target.__dict__:
            if target.__dict__[each_pos] is not None:
                pos = each_pos.split("__")[-1]
                if pos == "rotate":
                    dummy.rotate = target.__dict__[each_pos]
                elif pos == "scale":
                    dummy.scale = target.__dict__[each_pos]
                elif pos == "border_radius":
                    dummy.border_radius = target.__dict__[each_pos]
                elif pos == "alignment":
                    dummy.alignment = target.__dict__[each_pos]
                elif pos == "padding":
                    dummy.padding = target.__dict__[each_pos]
                elif pos == "horizontal_alignment":
                    dummy.horizontal_alignment = target.__dict__[each_pos]
                elif pos == "vertical_alignment":
                    dummy.vertical_alignment = target.__dict__[each_pos]
                elif pos == "top":
                    dummy.top = target.__dict__[each_pos]
                elif pos == "bottom":
                    dummy.bottom = target.__dict__[each_pos]
                elif pos == "left":
                    dummy.left = target.__dict__[each_pos]
                elif pos == "right":
                    dummy.right = target.__dict__[each_pos]
                elif pos == "rows":
                    dummy.rows = [
                        ft.DataRow(
                            [
                                (
                                    ft.DataCell(tube(100))
                                    if each_col.content.data == "shimmer_load"
                                    else ft.DataCell(ft.Text())
                                )
                                for each_col in each_control.cells
                            ]
                        )
                        for each_control in target.__dict__[each_pos]
                    ]
                elif pos == "columns":
                    dummy.columns = [
                        (
                            ft.DataColumn(tube(100))
                            if each_control.label.data == "shimmer_load"
                            else ft.DataColumn(ft.Text())
                        )
                        for each_control in target.__dict__[each_pos]
                    ]

        if content:
            dummy.content = self.create_dummy(target.content)
        if title:
            dummy.title = self.create_dummy(target.title)
        if subtitle:
            dummy.subtitle = self.create_dummy(target.subtitle)
        if leading:
            dummy.leading = self.create_dummy(target.leading)
        if trailing:
            dummy.trailing = self.create_dummy(target.trailing)
        if controls:
            try:
                dummy.controls = [
                    self.create_dummy(each_control) for each_control in target.controls
                ]
            except Exception as e:
                logging.error("EXCEPTION", e)
                temp = []
                for each_control in target.controls:
                    try:
                        temp.append(self.create_dummy(each_control))
                    except Exception as e:
                        logging.error("EXCEPTION", e)
                dummy.controls = temp

        if target.data == "shimmer_load":
            dummy.bgcolor = ft.Colors.with_opacity(opacity, color)
        return ft.Container(ft.Stack([dummy]), bgcolor=self.__color1)

    def did_mount(self):
        self.task = self.page.run_task(self.shine_async)

    def will_unmount(self):
        self.task.cancel()

def setup_theme_settings(page: ft.Page, color_scheme: str, radius: int, shape_type: str = None):
    """
    Setup the theme settings for the Flet page.
    Args:
        page (ft.Page): The Flet page to apply the theme settings to.
        color_scheme (str): The color scheme to use (e.g., "light", "dark").
        radius (int): The border radius for the controls.
        shape_type (str): The shape type for the controls. Default is "roundedRectangle".
    """
    if shape_type == "roundedRectangle":
        shape = ft.RoundedRectangleBorder(radius)
    elif shape_type == "beveledRectangle":
        shape = ft.BeveledRectangleBorder(radius)
    elif shape_type == "continuousRectangle":
        shape = ft.ContinuousRectangleBorder(radius)
    page.theme = ft.Theme(
        color_scheme_seed=color_scheme,
        visual_density=ft.VisualDensity.COMPACT,
        page_transitions=ft.PageTransitionsTheme(
            linux=ft.PageTransitionTheme.FADE_FORWARDS,
            windows=ft.PageTransitionTheme.FADE_FORWARDS,
        ),
        card_theme=ft.CardTheme(
            shape=shape,
            margin=ft.Margin(0, 4, 0, 0),
        ),
        text_button_theme=ft.TextButtonTheme(
            shape=shape,
        ),
        elevated_button_theme=ft.ElevatedButtonTheme(
            shape=shape,
        ),
        outlined_button_theme=ft.OutlinedButtonTheme(
            shape=shape,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            foreground_color=ft.Colors.ON_SECONDARY_CONTAINER,
            border_side=ft.BorderSide(
                color=ft.Colors.TRANSPARENT,
                width=0,
            ),
        ),
        icon_button_theme=ft.IconButtonTheme(
            shape=shape,
        ),
        floating_action_button_theme=ft.FloatingActionButtonTheme(
            shape=shape,
        ),
        appbar_theme=ft.AppBarTheme(
            shape=shape,
        ),
        list_tile_theme=ft.ListTileTheme(
            shape=shape,
        ),
        dialog_theme=ft.DialogTheme(
            shape=shape,
        ),
    )
