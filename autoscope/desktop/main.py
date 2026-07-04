"""Entry point for the AutoScope desktop application."""

import flet as ft

from autoscope.desktop.app import main as app_main


def main() -> None:
    ft.run(app_main)


if __name__ == "__main__":
    main()
