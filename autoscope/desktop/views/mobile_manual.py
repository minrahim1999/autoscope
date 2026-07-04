"""Mobile Manual recorder view for the desktop app."""

import threading
import time
from pathlib import Path
from typing import Optional

import flet as ft

from autoscope.desktop.recorder.mobile_recorder import MobileRecorder
from autoscope.desktop.recorder.script_builder import RecordedAction
from autoscope.desktop.views.common import _snack, _section_title, _ui_call

_BLANK_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


class MobileManualViewMixin:
    def _show_mobile_manual(self) -> None:
        name_field = ft.TextField(
            label="Script name",
            value="mobile_recording",
            width=240,
            prefix_icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
        )
        video_checkbox = ft.Checkbox(label="Record video", value=False)
        status_text = ft.Text("Ready", color=ft.Colors.ON_SURFACE_VARIANT)
        screen_image = ft.Image(
            src=_BLANK_IMAGE,
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

        def on_frame(data_uri: str) -> None:
            def update() -> None:
                screen_image.src = data_uri
                screen_image.update()

            _ui_call(self.page, update)

        def on_status(message: str) -> None:
            def update() -> None:
                status_text.value = message
                status_text.color = (
                    ft.Colors.ERROR if "not responding" in message else ft.Colors.ON_SURFACE_VARIANT
                )
                status_text.update()

            _ui_call(self.page, update)

        def start_stream(_: ft.ControlEvent) -> None:
            if self._mobile_recorder and self._mobile_recorder.is_recording:
                _snack(self.page, "Already streaming")
                return
            try:
                self._mobile_recorder = MobileRecorder(self.config)
                self._mobile_recorder.set_callbacks(add_action_log, on_frame)
                self._mobile_recorder.set_status_callback(on_status)
                status_text.value = "Connecting to device..."
                status_text.update()
                run_button.disabled = True
                run_button.update()
                last_script_path["path"] = None

                def launch() -> None:
                    try:
                        self._mobile_recorder.start(name_field.value, record_video=video_checkbox.value)
                        _ui_call(
                            self.page,
                            lambda: _snack(
                                self.page,
                                f"Connected to {self._mobile_recorder.serial}",
                            ),
                        )
                        _ui_call(
                            self.page,
                            lambda: (
                                setattr(status_text, "value", "Streaming..."),
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
                                _snack(self.page, f"Failed to connect: {err}", ft.Colors.ERROR),
                            ),
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
            screenshot_button.disabled = True
            screenshot_button.update()

            def stop() -> None:
                try:
                    path = self._mobile_recorder.stop()
                    video_path = self._mobile_recorder.video_path
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
                            setattr(screen_image, "src", _BLANK_IMAGE),
                            screen_image.update(),
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
            if not self._mobile_recorder or not self._mobile_recorder.is_recording:
                _snack(self.page, "Start stream first")
                return
            name = f"manual_{int(time.time())}.png"
            self._mobile_recorder.take_screenshot(name)
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
            x = int(e.local_position.x)
            y = int(e.local_position.y)
            self._mobile_recorder.tap(x, y, container_width, container_height)
            _snack(self.page, f"Tapped ({x}, {y})")

        # Swipe support: on_tap_down gives us the true start position (it fires
        # before the gesture arena decides tap vs. drag); on_pan_update deltas
        # are accumulated onto it to get an end position for on_pan_end. A small
        # distance deadzone keeps ordinary taps (handled by on_tap above) from
        # also registering as a zero-length swipe.
        swipe_origin = {"x": 0.0, "y": 0.0}
        swipe_current = {"x": 0.0, "y": 0.0}
        SWIPE_DEADZONE = 12

        def on_tap_down(e: ft.TapEvent) -> None:
            swipe_origin["x"] = swipe_current["x"] = e.local_position.x
            swipe_origin["y"] = swipe_current["y"] = e.local_position.y

        def on_pan_update(e: ft.DragUpdateEvent) -> None:
            swipe_current["x"] += e.local_delta.x
            swipe_current["y"] += e.local_delta.y

        def on_pan_end(_: ft.DragEndEvent) -> None:
            if not self._mobile_recorder or not self._mobile_recorder.is_recording:
                return
            dx = swipe_current["x"] - swipe_origin["x"]
            dy = swipe_current["y"] - swipe_origin["y"]
            if (dx * dx + dy * dy) ** 0.5 < SWIPE_DEADZONE:
                return
            x1, y1 = int(swipe_origin["x"]), int(swipe_origin["y"])
            x2, y2 = int(swipe_current["x"]), int(swipe_current["y"])
            self._mobile_recorder.swipe(x1, y1, x2, y2, container_width, container_height)
            _snack(self.page, f"Swiped ({x1}, {y1}) -> ({x2}, {y2})")

        screen_with_gesture = ft.GestureDetector(
            content=ft.Container(
                width=container_width,
                height=container_height,
                border_radius=12,
                bgcolor=ft.Colors.BLACK,
                content=screen_image,
            ),
            on_tap_up=on_tap,
            on_tap_down=on_tap_down,
            on_pan_update=on_pan_update,
            on_pan_end=on_pan_end,
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
                        ft.Container(content=name_field, col={"xs": 12, "sm": 12, "md": 4, "lg": 3}),
                        ft.Container(content=video_checkbox, col={"xs": 12, "sm": 6, "md": 2, "lg": 2}),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Connect & Stream",
                                icon=ft.Icons.FIBER_MANUAL_RECORD,
                                on_click=start_stream,
                                bgcolor=ft.Colors.ERROR_CONTAINER,
                                color=ft.Colors.ON_ERROR_CONTAINER,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Stop & Save",
                                icon=ft.Icons.STOP,
                                on_click=stop_stream,
                            ),
                            col={"xs": 12, "sm": 6, "md": 3, "lg": 2},
                        ),
                        ft.Container(content=screenshot_button, col={"xs": 6, "sm": 3, "md": 1, "lg": 1}),
                        ft.Container(content=run_button, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
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
