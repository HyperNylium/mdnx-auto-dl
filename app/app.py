from nicegui import ui

from __appdata__.modules.webui.PageConfig import (
    get_nav_pages, get_sub_pages, nav_to
)


ui.page_title("mdnx-auto-dl WebUI")
ui.dark_mode().enable()


drawer = ui.left_drawer(value=False).props("overlay behavior=mobile bordered")

with drawer:
    pages = get_nav_pages()
    for page in pages:
        ui.button(page.label, on_click=nav_to(page.path, drawer=drawer, close_drawer=True)) \
            .props("flat color=primary no-caps") \
            .classes("full-width justify-start q-ma-sm")


with ui.header().classes("q-pa-none items-center").style("height: 64px"):

    with ui.row().classes("full-width full-height items-center relative-position q-px-md"):
        ui.label("mdnx-auto-dl").classes("text-h6")

        with ui.row().classes("absolute-center gt-sm items-center q-gutter-sm"):
            pages = get_nav_pages()
            for page in pages:
                ui.button(page.label, on_click=nav_to(page.path, drawer=drawer, close_drawer=False)) \
                    .props("outline color=white no-caps")

        ui.space()

        ui.button(icon="menu", on_click=drawer.toggle) \
            .props("flat round color=white") \
            .classes("lt-md")


with ui.element("div").classes("w-full").style("height: 80vh;"):
    ui.sub_pages(get_sub_pages()).classes("w-full h-full")


ui.run(host="localhost", port=8080, reload=False, show=False, show_welcome_message=True)
