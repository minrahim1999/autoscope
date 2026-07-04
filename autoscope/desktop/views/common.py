"""Shared UI helpers used across desktop app views."""

from typing import Callable, Optional

import flet as ft


def _ui_call(page: ft.Page, fn: Callable[[], None]) -> None:
    """Run a synchronous UI-mutating callback on the page's event loop.

    Flet's page.run_task() requires an async coroutine function and raises
    TypeError otherwise. Background threads (adb streaming, recorders,
    subprocess runners) need this bridge to touch controls safely.
    """

    async def _runner() -> None:
        fn()

    page.run_task(_runner)


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
