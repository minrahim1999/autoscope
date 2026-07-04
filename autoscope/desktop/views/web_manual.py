"""Web Manual recorder view for the desktop app."""

import threading
import time
from pathlib import Path
from typing import Optional

import flet as ft

from autoscope.desktop.recorder.script_builder import RecordedAction
from autoscope.desktop.recorder.web_recorder import WebRecorder
from autoscope.desktop.views.common import _snack, _section_title, _ui_call


class WebManualViewMixin:
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
        video_checkbox = ft.Checkbox(label="Record video", value=False)
        status_text = ft.Text("Ready", color=ft.Colors.ON_SURFACE_VARIANT)
        action_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        last_script_path: dict = {"path": None}

        run_button = ft.ElevatedButton(
            "Run Test",
            icon=ft.Icons.PLAY_ARROW,
            disabled=True,
        )
        screenshot_button = ft.IconButton(
            icon=ft.Icons.CAMERA_ALT,
            tooltip="Take screenshot",
            disabled=True,
        )

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

            _ui_call(self.page, update)

        def start_recording(_: ft.ControlEvent) -> None:
            if self._web_recorder and self._web_recorder.is_recording:
                _snack(self.page, "Already recording")
                return
            try:
                self._web_recorder = WebRecorder(self.config)
                self._web_recorder.set_callback(add_action_log)
                status_text.value = "Starting browser..."
                status_text.update()
                run_button.disabled = True
                run_button.update()
                last_script_path["path"] = None

                def launch() -> None:
                    try:
                        self._web_recorder.start(
                            url_field.value,
                            name_field.value,
                            headless=False,
                            record_video=video_checkbox.value,
                        )
                        _ui_call(
                            self.page,
                            lambda: _snack(self.page, f"Recording started: {url_field.value}"),
                        )
                        _ui_call(
                            self.page,
                            lambda: (
                                setattr(status_text, "value", "Recording..."),
                                status_text.update(),
                                setattr(screenshot_button, "disabled", False),
                                screenshot_button.update(),
                            ),
                        )
                    except Exception as e:
                        _ui_call(
                            self.page,
                            lambda err=str(e): (
                                setattr(status_text, "value", f"Error: {err}"),
                                status_text.update(),
                                _snack(self.page, f"Failed to start: {err}", ft.Colors.ERROR),
                            ),
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
            screenshot_button.disabled = True
            screenshot_button.update()

            def stop() -> None:
                try:
                    path = self._web_recorder.stop()
                    video_path = self._web_recorder.video_path
                    last_script_path["path"] = path
                    msg = f"Script saved to {path}" if path else "No script saved"
                    if video_path:
                        msg += f"  |  video saved to {video_path}"
                    _ui_call(
                        self.page,
                        lambda: (
                            _snack(self.page, msg),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                            setattr(run_button, "disabled", path is None),
                            run_button.update(),
                        ),
                    )
                except Exception as e:
                    _ui_call(
                        self.page,
                        lambda err=str(e): _snack(self.page, f"Error stopping: {err}", ft.Colors.ERROR),
                    )

            threading.Thread(target=stop, daemon=True).start()

        def take_screenshot(_: ft.ControlEvent) -> None:
            if not self._web_recorder or not self._web_recorder.is_recording:
                _snack(self.page, "Start recording first")
                return
            name = f"manual_{int(time.time())}.png"
            self._web_recorder.take_screenshot(name)
            _snack(self.page, f"Screenshot saved: {name}")

        def run_test(_: ft.ControlEvent) -> None:
            path: Optional[Path] = last_script_path["path"]
            if not path:
                _snack(self.page, "Record and save a script first", ft.Colors.ERROR)
                return
            run_button.disabled = True
            run_button.update()
            status_text.value = f"Running {path.name}..."
            status_text.update()

            def run() -> None:
                try:
                    # Reuses the same ScriptRunner instance the Auto Run tab
                    # drives, so a just-recorded script can be replayed
                    # immediately without leaving this view.
                    result = self._script_runner.run_and_report(path)
                    status = result.get("status", "unknown")
                    duration = result.get("duration_seconds", 0)
                    msg = f"Run {status} in {duration:.2f}s"
                    _ui_call(
                        self.page,
                        lambda: (
                            _snack(self.page, msg, ft.Colors.GREEN if status == "passed" else ft.Colors.ERROR),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                            setattr(run_button, "disabled", False),
                            run_button.update(),
                        ),
                    )
                except Exception as e:
                    _ui_call(
                        self.page,
                        lambda err=str(e): (
                            _snack(self.page, f"Run error: {err}", ft.Colors.ERROR),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                            setattr(run_button, "disabled", False),
                            run_button.update(),
                        ),
                    )

            threading.Thread(target=run, daemon=True).start()

        run_button.on_click = run_test
        screenshot_button.on_click = take_screenshot

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
                        ft.Container(content=url_field, col={"xs": 12, "sm": 12, "md": 6, "lg": 5}),
                        ft.Container(content=name_field, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
                        ft.Container(content=video_checkbox, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Start Recording",
                                icon=ft.Icons.FIBER_MANUAL_RECORD,
                                on_click=start_recording,
                                bgcolor=ft.Colors.ERROR_CONTAINER,
                                color=ft.Colors.ON_ERROR_CONTAINER,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Stop & Save",
                                icon=ft.Icons.STOP,
                                on_click=stop_recording,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(content=screenshot_button, col={"xs": 6, "sm": 3, "md": 1, "lg": 1}),
                        ft.Container(content=run_button, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
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
