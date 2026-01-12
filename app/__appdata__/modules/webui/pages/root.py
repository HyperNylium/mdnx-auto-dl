from nicegui import ui


def root_page() -> None:
    ui.label('Root page').classes('text-2xl font-bold')
    ui.label('This is the main content area.')
