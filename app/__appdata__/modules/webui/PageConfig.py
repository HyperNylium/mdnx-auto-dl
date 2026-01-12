from nicegui import ui
from dataclasses import dataclass

from .pages.root import root_page
from .pages.settings import settings_page
from .pages.add import add_page


@dataclass(frozen=True)
class PageDef:
    path: str
    label: str
    title: str
    view: object
    show_in_nav: bool = True


PAGES = [
    PageDef(
        path="/",
        label="Home",
        title="Home",
        view=root_page,
        show_in_nav=True,
    ),
    PageDef(
        path="/add",
        label="Add Series",
        title="Add Series",
        view=add_page,
        show_in_nav=True,
    ),
    PageDef(
        path="/settings",
        label="Settings",
        title="Settings",
        view=settings_page,
        show_in_nav=True,
    ),
]


def get_nav_pages() -> list[PageDef]:
    pages = []
    for page in PAGES:
        if page.show_in_nav == True:
            pages.append(page)

    return pages


def get_sub_pages() -> dict:
    routes = {}
    for page in PAGES:

        def _wrapped_view(p=page):
            ui.page_title(p.title)
            p.view()

        routes[page.path] = _wrapped_view

    return routes


def nav_to(path, drawer: ui.drawer = None, close_drawer=False):

    def _go():
        ui.navigate.to(path)

        if close_drawer == True and drawer is not None:
            drawer.toggle()

    return _go
