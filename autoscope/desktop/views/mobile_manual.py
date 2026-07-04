"""Mobile Manual recorder view for the desktop app."""

import threading

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

            def stop() -> None:
                try:
                    path = self._mobile_recorder.stop()
                    msg = f"Script saved to {path}" if path else "No script saved"
                    _ui_call(
                        self.page,
                        lambda: (
                            _snack(self.page, msg),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                            setattr(screen_image, "src", _BLANK_IMAGE),
                            screen_image.update(),
                        ),
                    )
                except Exception as e:
                    _ui_call(
                        self.page,
                        lambda err=str(e): _snack(self.page, f"Error stopping: {err}", ft.Colors.ERROR),
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
            x = int(e.local_position.x)
            y = int(e.local_position.y)
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
