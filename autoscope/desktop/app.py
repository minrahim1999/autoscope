"""Flet desktop application for AutoScope."""

import os
from typing import Optional

import flet as ft

from autoscope.config.loader import load_config
from autoscope.desktop.paths import get_app_dir, get_config_path, is_packaged
from autoscope.desktop.recorder.mobile_recorder import MobileRecorder
from autoscope.desktop.recorder.web_recorder import WebRecorder
from autoscope.desktop.runner.script_runner import ScriptRunner
from autoscope.desktop.setup import check_adb, check_playwright_browsers, install_playwright_browsers
from autoscope.desktop.views.auto_run import AutoRunViewMixin
from autoscope.desktop.views.common import _snack
from autoscope.desktop.views.home import HomeViewMixin
from autoscope.desktop.views.mobile_manual import MobileManualViewMixin
from autoscope.desktop.views.reports import ReportsViewMixin
from autoscope.desktop.views.web_manual import WebManualViewMixin


class DesktopApp(
    HomeViewMixin,
    WebManualViewMixin,
    MobileManualViewMixin,
    AutoRunViewMixin,
    ReportsViewMixin,
):
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        # Ensure packaged apps use a writable app-data directory for config/scripts/reports.
        if is_packaged():
            os.environ["AUTOMATE_TESTER_HOME"] = str(get_app_dir())
            config_path = get_config_path()
            if config_path.exists():
                os.environ["AUTOMATE_TESTER_CONFIG"] = str(config_path)
        self.config = load_config()
        self._web_recorder: Optional[WebRecorder] = None
        self._mobile_recorder: Optional[MobileRecorder] = None
        self._script_runner = ScriptRunner(self.config)
        self._theme_button: Optional[ft.IconButton] = None

        self._setup_page()
        self._build_ui()
        self._selected_index = 0
        self._show_environment_check()
        self._navigate(0)

    def _show_environment_check(self) -> None:
        """Check external dependencies and offer to install Playwright browsers."""
        adb_ok, adb_msg = check_adb()
        browser_ok, browser_msg = check_playwright_browsers()

        def install_browsers(e: ft.ControlEvent) -> None:
            e.control.text = "Installing..."
            e.control.disabled = True
            e.control.update()
            ok, msg = install_playwright_browsers()
            color = ft.Colors.GREEN if ok else ft.Colors.ERROR
            _snack(self.page, msg, color)
            if ok:
                dlg.open = False
                self.page.update()

        if not browser_ok:
            dlg = ft.AlertDialog(
                title=ft.Text("Playwright browsers not installed"),
                content=ft.Text(
                    f"{browser_msg}\n\n"
                    "Click Install to download Chromium (required for web recording and auto tests)."
                ),
                actions=[
                    ft.TextButton("Install Chromium", on_click=install_browsers),
                    ft.TextButton("Close", on_click=lambda _: setattr(dlg, "open", False) or self.page.update()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

        if not adb_ok:
            _snack(self.page, adb_msg, ft.Colors.AMBER)

    def _setup_page(self) -> None:
        self.page.title = "AutoScope"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.INDIGO,
            use_material3=True,
        )
        self.page.padding = 0
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.min_width = 720
        self.page.window.min_height = 540
        self.page.window.resizable = True
        self.page.on_resized = self._on_resized

    def _on_resized(self, e) -> None:
        """Re-layout the current view when the window size changes."""
        self._navigate(self._selected_index)

    def _build_ui(self) -> None:
        self.content_area = ft.Container(expand=True, padding=24)

        self.navigation_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=130,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.WEB_OUTLINED,
                    selected_icon=ft.Icons.WEB,
                    label="Web Manual",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SMARTPHONE_OUTLINED,
                    selected_icon=ft.Icons.SMARTPHONE,
                    label="Mobile Manual",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PLAY_CIRCLE_OUTLINED,
                    selected_icon=ft.Icons.PLAY_CIRCLE,
                    label="Auto Run",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ASSESSMENT_OUTLINED,
                    selected_icon=ft.Icons.ASSESSMENT,
                    label="Reports",
                ),
            ],
            on_change=lambda e: self._navigate(e.control.selected_index),
        )

        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        self._theme_button = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE,
            tooltip="Toggle theme",
            on_click=self._toggle_theme,
        )

        self.page.add(
            ft.Row(
                expand=True,
                controls=[
                    ft.Column(
                        width=130,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(expand=True, content=self.navigation_rail),
                            ft.Container(
                                padding=8,
                                content=self._theme_button,
                            ),
                        ],
                    ),
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ],
            )
        )

    def _toggle_theme(self, _: ft.ControlEvent) -> None:
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self._theme_button.icon = ft.Icons.DARK_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self._theme_button.icon = ft.Icons.LIGHT_MODE
        self._theme_button.tooltip = "Toggle theme"
        self.page.update()

    def _navigate(self, index: int) -> None:
        self._selected_index = index
        if self.navigation_rail:
            self.navigation_rail.selected_index = index
        try:
            if index == 0:
                self._show_home()
            elif index == 1:
                self._show_web_manual()
            elif index == 2:
                self._show_mobile_manual()
            elif index == 3:
                self._show_auto_run()
            elif index == 4:
                self._show_reports()
        except Exception as e:
            _snack(self.page, f"Navigation error: {e}", ft.Colors.ERROR)
        self.page.update()


def main(page: ft.Page) -> None:
    DesktopApp(page)
