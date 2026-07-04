"""Web Manual recorder view for the desktop app."""

import threading

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

                def launch() -> None:
                    try:
                        self._web_recorder.start(url_field.value, name_field.value, headless=False)
                        _ui_call(
                            self.page,
                            lambda: _snack(self.page, f"Recording started: {url_field.value}"),
                        )
                        _ui_call(
                            self.page,
                            lambda: (setattr(status_text, "value", "Recording..."), status_text.update()),
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

            def stop() -> None:
                try:
                    path = self._web_recorder.stop()
                    msg = f"Script saved to {path}" if path else "No script saved"
                    _ui_call(
                        self.page,
                        lambda: (
                            _snack(self.page, msg),
                            setattr(status_text, "value", "Ready"),
                            status_text.update(),
                        ),
                    )
                except Exception as e:
                    _ui_call(
                        self.page,
                        lambda err=str(e): _snack(self.page, f"Error stopping: {err}", ft.Colors.ERROR),
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
