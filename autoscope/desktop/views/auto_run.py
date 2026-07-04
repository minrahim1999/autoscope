"""Auto Run view for the desktop app."""

import threading
from pathlib import Path
from typing import Optional

import flet as ft

from autoscope.desktop.paths import get_scripts_dir
from autoscope.desktop.runner.script_runner import ScriptRunner
from autoscope.desktop.views.common import _snack, _section_title, _ui_call


class AutoRunViewMixin:
    def _show_auto_run(self) -> None:
        script_list = ft.ListView(expand=True, spacing=8)
        result_text = ft.Text("Select a script and click Run", color=ft.Colors.ON_SURFACE_VARIANT)
        progress = ft.ProgressRing(visible=False, width=24, height=24)
        selected_script: Optional[Path] = None

        def refresh_scripts() -> None:
            script_list.controls.clear()
            scripts = ScriptRunner.discover_scripts(get_scripts_dir())
            if not scripts:
                script_list.controls.append(
                    ft.Text("No scripts found. Record a manual test first.", italic=True)
                )
            else:
                for script in scripts:
                    platform = ScriptRunner.detect_platform(script)
                    if platform == "web":
                        icon = ft.Icons.WEB
                    elif platform == "ios":
                        icon = ft.Icons.PHONE_IPHONE
                    else:
                        icon = ft.Icons.SMARTPHONE
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
                    _ui_call(
                        self.page,
                        lambda: (
                            _snack(self.page, msg, ft.Colors.GREEN if status == "passed" else ft.Colors.ERROR),
                            setattr(result_text, "value", msg),
                            result_text.update(),
                            setattr(progress, "visible", False),
                            progress.update(),
                        ),
                    )
                except Exception as e:
                    _ui_call(
                        self.page,
                        lambda err=str(e): (
                            _snack(self.page, f"Run error: {err}", ft.Colors.ERROR),
                            setattr(result_text, "value", f"Error: {err}"),
                            result_text.update(),
                            setattr(progress, "visible", False),
                            progress.update(),
                        ),
                    )

            threading.Thread(target=run, daemon=True).start()

        refresh_scripts()

        self.content_area.content = ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                _section_title("Auto Run", ft.Icons.PLAY_CIRCLE),
                # Row(wrap=True) reflows based on real measured width instead
                # of ResponsiveRow's breakpoint guessing (see home.py).
                ft.Row(
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.ElevatedButton(
                            "Refresh",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda _: (refresh_scripts(), self.page.update()),
                        ),
                        ft.ElevatedButton(
                            "Run Selected",
                            icon=ft.Icons.PLAY_ARROW,
                            on_click=run_script,
                        ),
                        progress,
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
