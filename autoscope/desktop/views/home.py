"""Home view for the desktop app."""

from typing import Callable

import flet as ft

_CARD_WIDTH = 260
_CARD_HEIGHT = 240


class HomeViewMixin:
    def _show_home(self) -> None:
        def card(title: str, subtitle: str, icon, on_click: Callable) -> ft.Card:
            return ft.Card(
                elevation=2,
                width=_CARD_WIDTH,
                height=_CARD_HEIGHT,
                content=ft.Container(
                    padding=24,
                    on_click=on_click,
                    border_radius=16,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(icon, size=56, color=ft.Colors.PRIMARY),
                            ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(subtitle, size=14, text_align=ft.TextAlign.CENTER),
                        ],
                    ),
                ),
            )

        self.content_area.content = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=32,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(
                    "AutoScope",
                    size=40,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PRIMARY,
                ),
                ft.Text(
                    "Record manual interactions and replay them automatically for web, Android, and iOS.",
                    size=16,
                    text_align=ft.TextAlign.CENTER,
                ),
                # Row(wrap=True) reflows based on the actual measured width of
                # this container, unlike ResponsiveRow (whose Bootstrap-style
                # breakpoints are keyed to an ambiguous reference width that
                # doesn't account for the nav rail eating into the available
                # space) -- so this stays readable at any window size instead
                # of picking a column count that doesn't leave room to fit.
                ft.Row(
                    wrap=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=24,
                    run_spacing=24,
                    controls=[
                        card(
                            "Web Manual",
                            "Open a browser, record clicks and inputs, then generate a script.",
                            ft.Icons.WEB,
                            lambda _: self._navigate(1),
                        ),
                        card(
                            "Android Manual",
                            "Stream your Android device, tap and type, then generate a script.",
                            ft.Icons.SMARTPHONE,
                            lambda _: self._navigate(2),
                        ),
                        card(
                            "iOS Manual",
                            "Stream a Simulator/device via WebDriverAgent, tap and type, then generate a script.",
                            ft.Icons.PHONE_IPHONE,
                            lambda _: self._navigate(3),
                        ),
                        card(
                            "Auto Run",
                            "Run generated scripts and view pass/fail reports.",
                            ft.Icons.PLAY_CIRCLE,
                            lambda _: self._navigate(4),
                        ),
                    ],
                ),
            ],
        )
