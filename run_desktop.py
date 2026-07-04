#!/usr/bin/env python3
"""Launch the AutoScope desktop application."""

import flet as ft

from autoscope.desktop.app import main as app_main


if __name__ == "__main__":
    ft.run(app_main)
