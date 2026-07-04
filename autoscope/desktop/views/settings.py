"""Settings view: lets the user choose where scripts and reports are saved."""

import asyncio
from typing import Callable

import flet as ft

from autoscope.desktop import settings as desktop_settings
from autoscope.desktop.folder_picker import choose_directory
from autoscope.desktop.paths import get_reports_dir, get_scripts_dir
from autoscope.desktop.views.common import _section_title, _snack


class SettingsViewMixin:
    def _show_settings(self) -> None:
        scripts_path_text = ft.Text(str(get_scripts_dir()), selectable=True)
        reports_path_text = ft.Text(str(get_reports_dir()), selectable=True)

        scripts_reset_button = ft.TextButton(
            "Reset to default",
            icon=ft.Icons.RESTORE,
            disabled=desktop_settings.get_scripts_dir_override() is None,
        )
        reports_reset_button = ft.TextButton(
            "Reset to default",
            icon=ft.Icons.RESTORE,
            disabled=desktop_settings.get_reports_dir_override() is None,
        )

        async def choose_scripts_dir(_: ft.ControlEvent) -> None:
            # choose_directory() blocks on a subprocess until the user picks
            # or cancels; run it off Flet's event loop so the UI stays responsive.
            chosen = await asyncio.to_thread(
                choose_directory,
                "Choose a folder for generated scripts",
                str(get_scripts_dir()),
            )
            if not chosen:
                return
            desktop_settings.set_scripts_dir_override(chosen)
            scripts_path_text.value = str(get_scripts_dir())
            scripts_reset_button.disabled = False
            scripts_path_text.update()
            scripts_reset_button.update()
            _snack(self.page, f"Scripts will now be saved to {chosen}")

        async def choose_reports_dir(_: ft.ControlEvent) -> None:
            chosen = await asyncio.to_thread(
                choose_directory,
                "Choose a folder for reports",
                str(get_reports_dir()),
            )
            if not chosen:
                return
            desktop_settings.set_reports_dir_override(chosen)
            reports_path_text.value = str(get_reports_dir())
            reports_reset_button.disabled = False
            reports_path_text.update()
            reports_reset_button.update()
            _snack(self.page, f"Reports will now be saved to {chosen}")

        def reset_scripts_dir(_: ft.ControlEvent) -> None:
            desktop_settings.set_scripts_dir_override(None)
            scripts_path_text.value = str(get_scripts_dir())
            scripts_reset_button.disabled = True
            scripts_path_text.update()
            scripts_reset_button.update()
            _snack(self.page, "Scripts folder reset to default")

        def reset_reports_dir(_: ft.ControlEvent) -> None:
            desktop_settings.set_reports_dir_override(None)
            reports_path_text.value = str(get_reports_dir())
            reports_reset_button.disabled = True
            reports_path_text.update()
            reports_reset_button.update()
            _snack(self.page, "Reports folder reset to default")

        scripts_reset_button.on_click = reset_scripts_dir
        reports_reset_button.on_click = reset_reports_dir

        def folder_card(
            title: str,
            description: str,
            path_text: ft.Text,
            on_change: Callable[[ft.ControlEvent], None],
            reset_button: ft.TextButton,
        ) -> ft.Card:
            return ft.Card(
                elevation=1,
                content=ft.Container(
                    padding=20,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(description, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Container(
                                padding=10,
                                border_radius=8,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                content=path_text,
                            ),
                            ft.Row(
                                wrap=True,
                                spacing=8,
                                run_spacing=8,
                                controls=[
                                    ft.ElevatedButton(
                                        "Change...",
                                        icon=ft.Icons.FOLDER_OPEN,
                                        on_click=on_change,
                                    ),
                                    reset_button,
                                ],
                            ),
                        ],
                    ),
                ),
            )

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Settings", ft.Icons.SETTINGS),
                ft.Text(
                    "Changing a folder only affects new scripts/reports going forward — "
                    "existing files are not moved.",
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Row(
                    wrap=True,
                    spacing=16,
                    run_spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            width=420,
                            content=folder_card(
                                "Scripts folder",
                                "Where the Web/Android/iOS Manual recorders save generated "
                                "scripts, and where Auto Run looks for them.",
                                scripts_path_text,
                                choose_scripts_dir,
                                scripts_reset_button,
                            ),
                        ),
                        ft.Container(
                            width=420,
                            content=folder_card(
                                "Reports folder",
                                "Where Auto Run and the manual recorders write JSON/HTML "
                                "test reports.",
                                reports_path_text,
                                choose_reports_dir,
                                reports_reset_button,
                            ),
                        ),
                    ],
                ),
            ],
        )
