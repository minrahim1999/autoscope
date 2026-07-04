"""Flet desktop application for AutoScope."""

import base64
import io
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from autoscope.config.loader import load_config
from autoscope.desktop.paths import get_app_dir, get_config_path, get_reports_dir, is_packaged
from autoscope.desktop.recorder.mobile_recorder import MobileRecorder
from autoscope.desktop.recorder.script_builder import RecordedAction
from autoscope.desktop.recorder.web_recorder import WebRecorder
from autoscope.desktop.runner.script_runner import ScriptRunner
from autoscope.desktop.setup import check_adb, check_playwright_browsers, install_playwright_browsers


def _snack(page: ft.Page, message: str, color: Optional[str] = None) -> None:
    sb = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=color or ft.Colors.ON_PRIMARY_CONTAINER,
    )

    def _remove(_: ft.ControlEvent) -> None:
        if sb in page.overlay:
            page.overlay.remove(sb)
            page.update()

    sb.on_dismiss = _remove
    page.overlay.append(sb)
    sb.open = True
    page.update()


def _section_title(text: str, icon: Optional[str] = None) -> ft.Row:
    controls = []
    if icon:
        controls.append(ft.Icon(icon, size=28, color=ft.Colors.PRIMARY))
    controls.append(
        ft.Text(
            text,
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_SURFACE,
        )
    )
    return ft.Row(controls=controls, spacing=12)


class DesktopApp:
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
            color = ft.Colors.SUCCESS if ok else ft.Colors.ERROR
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
            _snack(self.page, adb_msg, ft.Colors.WARNING)

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

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------
    def _show_home(self) -> None:
        def card(title: str, subtitle: str, icon, on_click: Callable) -> ft.Card:
            return ft.Card(
                elevation=2,
                col={"xs": 12, "sm": 6, "md": 4, "lg": 4, "xl": 4},
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
                    "Record manual interactions and replay them automatically for web and mobile.",
                    size=16,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.ResponsiveRow(
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
                            "Mobile Manual",
                            "Stream your Android device, tap and type, then generate a script.",
                            ft.Icons.SMARTPHONE,
                            lambda _: self._navigate(2),
                        ),
                        card(
                            "Auto Run",
                            "Run generated scripts and view pass/fail reports.",
                            ft.Icons.PLAY_CIRCLE,
                            lambda _: self._navigate(3),
                        ),
                    ],
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Web Manual
    # ------------------------------------------------------------------
    def _show_web_manual(self) -> None:
        url_field = ft.TextField(
            label="Start URL",
            value=self.config.web.base_url,
            expand=True,
            prefix_icon=ft.Icons.LINK,
        )
        name_field = ft.TextField(
            label="Script name",
            value="web_recording",
            width=200,
            prefix_icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
        )
        status_text = ft.Text("Ready", color=ft.Colors.ON_SURFACE_VARIANT)
        action_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)

        def add_action_log(action: RecordedAction) -> None:
            def update() -> None:
                action_list.controls.append(
                    ft.Container(
                        padding=8,
                        border_radius=8,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        content=ft.Text(
                            f"{action.action}: {action.data}",
                            size=12,
                            no_wrap=False,
                        ),
                    )
                )
                action_list.update()

            self.page.run_task(update)

        def start_recording(_: ft.ControlEvent) -> None:
            if self._web_recorder and self._web_recorder.is_recording:
                _snack(self.page, "Already recording")
                return
            try:
                self._web_recorder = WebRecorder(self.config)
                self._web_recorder.set_callback(add_action_log)
                status_text.value = "Starting browser..."
                status_text.update()

                def launch() -> None:
                    try:
                        self._web_recorder.start(url_field.value, name_field.value, headless=False)
                        self.page.run_task(
                            lambda: _snack(self.page, f"Recording started: {url_field.value}")
                        )
                        self.page.run_task(lambda: setattr(status_text, "value", "Recording...") or status_text.update())
                    except Exception as e:
                        self.page.run_task(
                            lambda err=str(e): (
                                setattr(status_text, "value", f"Error: {err}"),
                                status_text.update(),
                                _snack(self.page, f"Failed to start: {err}", ft.Colors.ERROR),
                            )
                        )

                threading.Thread(target=launch, daemon=True).start()
            except Exception as e:
                _snack(self.page, f"Error: {e}", ft.Colors.ERROR)

        def stop_recording(_: ft.ControlEvent) -> None:
            if not self._web_recorder or not self._web_recorder.is_recording:
                _snack(self.page, "No active recording")
                return
            status_text.value = "Saving script..."
            status_text.update()

            def stop() -> None:
                try:
                    path = self._web_recorder.stop()
                    msg = f"Script saved to {path}" if path else "No script saved"
                    self.page.run_task(
                        lambda: (
                            _snack(self.page, msg),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                        )
                    )
                except Exception as e:
                    self.page.run_task(
                        lambda err=str(e): _snack(self.page, f"Error stopping: {err}", ft.Colors.ERROR)
                    )

            threading.Thread(target=stop, daemon=True).start()

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Web Manual Recorder", ft.Icons.WEB),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.Container(content=url_field, col={"xs": 12, "sm": 12, "md": 6, "lg": 6}),
                        ft.Container(content=name_field, col={"xs": 12, "sm": 6, "md": 3, "lg": 3}),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Start Recording",
                                icon=ft.Icons.FIBER_MANUAL_RECORD,
                                on_click=start_recording,
                                bgcolor=ft.Colors.ERROR_CONTAINER,
                                color=ft.Colors.ON_ERROR_CONTAINER,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 3},
                        ),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Stop & Save",
                                icon=ft.Icons.STOP,
                                on_click=stop_recording,
                            ),
                            col={"xs": 12, "sm": 12, "md": 3, "lg": 3},
                        ),
                    ],
                ),
                status_text,
                ft.Text("Recorded actions", weight=ft.FontWeight.BOLD),
                ft.Container(
                    expand=True,
                    border_radius=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    padding=12,
                    content=action_list,
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Mobile Manual
    # ------------------------------------------------------------------
    def _show_mobile_manual(self) -> None:
        name_field = ft.TextField(
            label="Script name",
            value="mobile_recording",
            width=240,
            prefix_icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
        )
        status_text = ft.Text("Ready", color=ft.Colors.ON_SURFACE_VARIANT)
        screen_image = ft.Image(
            src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            width=360,
            height=640,
            fit=ft.BoxFit.FILL,
            border_radius=ft.BorderRadius.all(12),
            gapless_playback=True,
        )
        input_field = ft.TextField(
            label="Type on device",
            hint_text="Text to send...",
            expand=True,
            prefix_icon=ft.Icons.KEYBOARD,
        )
        action_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        container_width = 360
        container_height = 640

        def add_action_log(action: RecordedAction) -> None:
            def update() -> None:
                action_list.controls.append(
                    ft.Container(
                        padding=8,
                        border_radius=8,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        content=ft.Text(
                            f"{action.action}: {action.data}",
                            size=12,
                            no_wrap=False,
                        ),
                    )
                )
                action_list.update()

            self.page.run_task(update)

        def on_frame(b64: str) -> None:
            def update() -> None:
                screen_image.src_base64 = b64.split(",", 1)[1]
                screen_image.update()

            self.page.run_task(update)

        def start_stream(_: ft.ControlEvent) -> None:
            if self._mobile_recorder and self._mobile_recorder.is_recording:
                _snack(self.page, "Already streaming")
                return
            try:
                self._mobile_recorder = MobileRecorder(self.config)
                self._mobile_recorder.set_callbacks(add_action_log, on_frame)
                status_text.value = "Connecting to device..."
                status_text.update()

                def launch() -> None:
                    try:
                        self._mobile_recorder.start(name_field.value)
                        self.page.run_task(
                            lambda: _snack(
                                self.page,
                                f"Connected to {self._mobile_recorder.serial}",
                            )
                        )
                        self.page.run_task(
                            lambda: (
                                setattr(status_text, "value", "Streaming..."),
                                status_text.update(),
                            )
                        )
                    except Exception as e:
                        self.page.run_task(
                            lambda err=str(e): (
                                setattr(status_text, "value", f"Error: {err}"),
                                status_text.update(),
                                _snack(self.page, f"Failed to connect: {err}", ft.Colors.ERROR),
                            )
                        )

                threading.Thread(target=launch, daemon=True).start()
            except Exception as e:
                _snack(self.page, f"Error: {e}", ft.Colors.ERROR)

        def stop_stream(_: ft.ControlEvent) -> None:
            if not self._mobile_recorder or not self._mobile_recorder.is_recording:
                _snack(self.page, "No active stream")
                return
            status_text.value = "Saving script..."
            status_text.update()

            def stop() -> None:
                try:
                    path = self._mobile_recorder.stop()
                    msg = f"Script saved to {path}" if path else "No script saved"
                    self.page.run_task(
                        lambda: (
                            _snack(self.page, msg),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                            setattr(screen_image, "src_base64", None),
                            screen_image.update(),
                        )
                    )
                except Exception as e:
                    self.page.run_task(
                        lambda err=str(e): _snack(self.page, f"Error stopping: {err}", ft.Colors.ERROR)
                    )

            threading.Thread(target=stop, daemon=True).start()

        def send_text(_: ft.ControlEvent) -> None:
            if not self._mobile_recorder or not self._mobile_recorder.is_recording:
                _snack(self.page, "Start stream first")
                return
            text = input_field.value or ""
            if not text:
                return
            self._mobile_recorder.input_text(text)
            _snack(self.page, f"Sent text: {text}")
            input_field.value = ""
            input_field.update()

        def on_tap(e: ft.TapEvent) -> None:
            if not self._mobile_recorder or not self._mobile_recorder.is_recording:
                return
            x = int(e.local_x)
            y = int(e.local_y)
            self._mobile_recorder.tap(x, y, container_width, container_height)
            _snack(self.page, f"Tapped ({x}, {y})")

        screen_with_gesture = ft.GestureDetector(
            content=ft.Container(
                width=container_width,
                height=container_height,
                border_radius=12,
                bgcolor=ft.Colors.BLACK,
                content=screen_image,
            ),
            on_tap_up=on_tap,
        )

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Mobile Manual Recorder", ft.Icons.SMARTPHONE),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.Container(content=name_field, col={"xs": 12, "sm": 12, "md": 6, "lg": 6}),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Connect & Stream",
                                icon=ft.Icons.FIBER_MANUAL_RECORD,
                                on_click=start_stream,
                                bgcolor=ft.Colors.ERROR_CONTAINER,
                                color=ft.Colors.ON_ERROR_CONTAINER,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 3},
                        ),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Stop & Save",
                                icon=ft.Icons.STOP,
                                on_click=stop_stream,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 3},
                        ),
                    ],
                ),
                status_text,
                ft.ResponsiveRow(
                    expand=True,
                    spacing=24,
                    run_spacing=24,
                    controls=[
                        ft.Column(
                            col={"xs": 12, "sm": 12, "md": 6, "lg": 5, "xl": 4},
                            controls=[
                                ft.Container(
                                    content=screen_with_gesture,
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Row(
                                    controls=[
                                        input_field,
                                        ft.IconButton(
                                            icon=ft.Icons.SEND,
                                            tooltip="Send to device",
                                            on_click=send_text,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Container(
                            col={"xs": 12, "sm": 12, "md": 6, "lg": 7, "xl": 8},
                            expand=True,
                            border_radius=12,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                            padding=12,
                            content=action_list,
                        ),
                    ],
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Auto Run
    # ------------------------------------------------------------------
    def _show_auto_run(self) -> None:
        script_list = ft.ListView(expand=True, spacing=8)
        result_text = ft.Text("Select a script and click Run", color=ft.Colors.ON_SURFACE_VARIANT)
        progress = ft.ProgressRing(visible=False, width=24, height=24)
        selected_script: Optional[Path] = None

        def refresh_scripts() -> None:
            script_list.controls.clear()
            scripts = ScriptRunner.discover_scripts(Path("scripts"))
            if not scripts:
                script_list.controls.append(
                    ft.Text("No scripts found. Record a manual test first.", italic=True)
                )
            else:
                for script in scripts:
                    platform = ScriptRunner.detect_platform(script)
                    icon = ft.Icons.WEB if platform == "web" else ft.Icons.SMARTPHONE
                    script_list.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(icon),
                            title=ft.Text(script.name),
                            subtitle=ft.Text(f"{platform} · {script}"),
                            on_click=lambda e, s=script: select_script(s),
                            selected=selected_script == script,
                        )
                    )
            # Update is deferred to the caller because this helper runs
            # before script_list is added to the page during initial build.

        def select_script(script: Path) -> None:
            nonlocal selected_script
            selected_script = script
            result_text.value = f"Selected: {script.name}"
            refresh_scripts()
            self.page.update()

        def run_script(_: ft.ControlEvent) -> None:
            if not selected_script:
                _snack(self.page, "Select a script first", ft.Colors.ERROR)
                return
            progress.visible = True
            progress.update()
            result_text.value = f"Running {selected_script.name}..."
            result_text.update()

            def run() -> None:
                try:
                    result = self._script_runner.run_and_report(selected_script)
                    status = result.get("status", "unknown")
                    duration = result.get("duration_seconds", 0)
                    html = result.get("html_report", "")
                    msg = f"Run {status} in {duration:.2f}s. Report: {html}"
                    self.page.run_task(
                        lambda: (
                            _snack(self.page, msg, ft.Colors.SUCCESS if status == "passed" else ft.Colors.ERROR),
                            setattr(result_text, "value", msg),
                            result_text.update(),
                            setattr(progress, "visible", False),
                            progress.update(),
                        )
                    )
                except Exception as e:
                    self.page.run_task(
                        lambda err=str(e): (
                            _snack(self.page, f"Run error: {err}", ft.Colors.ERROR),
                            setattr(result_text, "value", f"Error: {err}"),
                            result_text.update(),
                            setattr(progress, "visible", False),
                            progress.update(),
                        )
                    )

            threading.Thread(target=run, daemon=True).start()

        refresh_scripts()

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Auto Run", ft.Icons.PLAY_CIRCLE),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Refresh",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda _: (refresh_scripts(), self.page.update()),
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Run Selected",
                                icon=ft.Icons.PLAY_ARROW,
                                on_click=run_script,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(content=progress, col={"xs": 12, "sm": 12, "md": 1, "lg": 1}),
                    ],
                ),
                result_text,
                ft.Container(
                    expand=True,
                    border_radius=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    padding=12,
                    content=script_list,
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def _show_reports(self) -> None:
        report_dir = Path(self.config.runner.output_dir)
        reports = []
        if report_dir.exists():
            reports = sorted(report_dir.glob("*.html"), reverse=True)

        report_list = ft.ListView(expand=True, spacing=8)
        if not reports:
            report_list.controls.append(ft.Text("No reports yet. Run tests first.", italic=True))
        else:
            for report in reports:
                report_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.OPEN_IN_BROWSER),
                        title=ft.Text(report.name),
                        subtitle=ft.Text(str(report)),
                        trailing=ft.IconButton(
                            ft.Icons.OPEN_IN_NEW,
                            tooltip="Open in browser",
                            on_click=lambda _, r=report: webbrowser.open(f"file://{r.resolve()}"),
                        ),
                    )
                )

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Reports", ft.Icons.ASSESSMENT),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Open Reports Folder",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda _: self._open_folder(report_dir),
                            ),
                            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    border_radius=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    padding=12,
                    content=report_list,
                ),
            ],
        )

    def _open_folder(self, path: Path) -> None:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])


def main(page: ft.Page) -> None:
    DesktopApp(page)
