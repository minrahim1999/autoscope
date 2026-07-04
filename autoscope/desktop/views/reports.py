"""Reports view for the desktop app."""

import subprocess
import sys
import webbrowser
from pathlib import Path

import flet as ft

from autoscope.desktop.paths import get_reports_dir
from autoscope.desktop.views.common import _section_title


class ReportsViewMixin:
    def _show_reports(self) -> None:
        report_dir = get_reports_dir()
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
                ft.Row(
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.ElevatedButton(
                            "Open Reports Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda _: self._open_folder(report_dir),
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
