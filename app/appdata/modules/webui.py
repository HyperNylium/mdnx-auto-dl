from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from nicegui import ui

# Import existing config & constants
from appdata.modules.Vars import logger, config, CONFIG_PATH, LOG_FILE, QUEUE_PATH

def _read_queue() -> Dict[str, Any]:
    """Read queue.json freshly every time (so UI sees updates made by the manager)."""
    try:
        p = Path(QUEUE_PATH)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding='utf-8') or '{}')
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        logger.error(f"[WebUI] Failed to read queue.json: {e}")
        return {}

def _save_monitor_ids(new_ids: List[str]) -> None:
    """Persist monitor-series-id to config.json and update in-memory config here."""
    # Keep unique order based on appearance
    seen: Set[str] = set()
    ids_unique = [s for s in new_ids if not (s in seen or seen.add(s))]

    config["monitor-series-id"] = ids_unique

    # Write back to file atomically-ish
    tmp = Path(CONFIG_PATH).with_suffix('.json.tmp')
    final = Path(CONFIG_PATH)
    tmp.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding='utf-8')
    tmp.replace(final)

def _read_log_tail(max_bytes: int = 80_000) -> str:
    p = Path(LOG_FILE)
    if not p.exists():
        return "(log file not found)"
    try:
        size = p.stat().st_size
        with p.open('rb') as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            raw = f.read()
        return raw.decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"[WebUI] Failed to read log: {e}")
        return "(unable to read log)"

def _counts_for_series(series: Dict[str, Any]) -> Tuple[int, int]:
    """(downloaded, total) using episode flags; fallback to series.eps_count when needed."""
    total = 0
    done = 0
    for season in (series.get('seasons') or {}).values():
        eps = season.get('episodes') or {}
        total += len(eps)
        for ep in eps.values():
            if ep.get('episode_downloaded'):
                done += 1
    if total == 0:
        # fallback to metadata if episodes not populated yet
        try:
            total = int((series.get('series') or {}).get('eps_count') or 0)
        except Exception:
            pass
    return done, total

def start_webui(host='0.0.0.0', port=8080, dark_mode=True) -> None:
    # Run WebUI server (no app control here)
    ui.run(title='mdnx-auto-dl', reload=False, dark=dark_mode, host=host, port=port)


# IDs the user added that may not yet be in queue.json
optimistic_ids: Set[str] = set(config.get("monitor-series-id", []))



with ui.header().classes('bg-gray-900 text-white'):
    ui.label('mdnx-auto-dl').classes('text-lg font-semibold')
    ui.space()

    def open_log():
        with ui.dialog() as dlg, ui.card().classes('w-screen h-screen max-w-none p-0 flex flex-col'):
            dlg.props('maximized persistent')

            with ui.row().classes('items-center justify-between w-full px-4 py-3 bg-gray-800 text-white'):
                ui.label('Live Log').classes('text-lg font-semibold')
                with ui.row().classes('items-center gap-4'):
                    auto_scroll = ui.switch('Auto-scroll', value=True).props('dense')
                    close_btn = ui.button('Close').props('outline dense')

            log_view = ui.log().classes('flex-1 w-full h-full overflow-auto bg-black text-green-200 font-mono p-3')

            def refresh_log():
                content = _read_log_tail()
                lines = content.splitlines()[-2000:]
                log_view.clear()
                for ln in lines:
                    log_view.push(ln)
                if auto_scroll.value and lines:
                    ui.run_javascript(
                        f"""
                        const el = getHtmlElement('{log_view.id}');
                        if (el && el.lastElementChild) {{
                            el.lastElementChild.scrollIntoView({{behavior: 'auto', block: 'end'}});
                        }}
                        """
                    )

            refresh_log()
            t = ui.timer(1.0, refresh_log)
            close_btn.on('click', lambda: (t.cancel(), dlg.close()))

        dlg.open()

    ui.button('LOG', on_click=open_log).props('outline')



with ui.column().classes('max-w-6xl mx-auto w-full p-6 gap-6'):

    # Series ID input
    with ui.card().classes('w-full p-6'):
        ui.label('Series ID input').classes('text-xl font-semibold')

        with ui.row().classes('w-full justify-center'):
            with ui.column().classes('gap-2 w-full sm:w-96'):
                series_input = ui.input(
                    label='Series ID',
                    placeholder='e.g., GNVHKN94W',
                ).props('clearable filled maxlength=9').classes('w-full')

                with ui.row().classes('items-center w-full'):
                    btn_spinner = ui.spinner(size='md').classes('text-blue-400 mr-2').style('display:none')
                    btn_add = ui.button('Add to queue').props('unelevated').classes('flex-1')

                async def set_busy(is_busy: bool):
                    (series_input.disable() if is_busy else series_input.enable())
                    (btn_add.disable() if is_busy else btn_add.enable())
                    btn_spinner.style('display:inline-block' if is_busy else 'display:none')

                async def add_clicked(e=None):
                    value = (series_input.value or '').strip()
                    if not value:
                        ui.notify('Please enter a Series ID', color='negative'); return
                    if len(value) > 9:
                        ui.notify('Series ID must be at most 9 characters', color='negative'); return

                    await set_busy(True)
                    await asyncio.sleep(0)  # let disabled & spinner render

                    try:
                        # Update monitor list in config.json
                        current = list(config.get("monitor-series-id", []))
                        if value in current:
                            ui.notify('Series already in monitor list', color='warning')
                        else:
                            current.append(value)
                            _save_monitor_ids(current)
                            ui.notify(f'Added "{value}"', color='positive')

                        # optimistic appearance in UI
                        optimistic_ids.add(value)
                        render_queue.refresh()
                        series_input.value = ''
                    except Exception as ex:
                        ui.notify(str(ex), color='negative')
                    finally:
                        await set_busy(False)

                btn_add.on('click', add_clicked)
                series_input.on('keydown.enter', add_clicked)

    ui.separator().classes('my-2')

    # queue view
    ui.label('Queue').classes('text-xl font-semibold')

    @ui.refreshable
    def render_queue() -> None:
        data = _read_queue()

        # Combine optimistic IDs with those actually in queue.json
        ordered_ids: List[str] = []
        ordered_ids.extend(sorted(optimistic_ids))
        for sid in data.keys():
            if sid not in ordered_ids:
                ordered_ids.append(sid)

        if not ordered_ids:
            ui.label('Nothing queued yet — add a Series ID above.').classes('text-gray-500 italic')
            return

        for sid in ordered_ids:
            series = data.get(sid)
            name = (series or {}).get('series', {}).get('series_name') or '(pending...)'
            done, total = _counts_for_series(series) if series else (0, 0)

            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-start justify-between w-full'):
                    with ui.column().classes('gap-1'):
                        ui.label(name).classes('font-semibold text-base')
                        ui.label(f'ID: {sid}').classes('text-xs text-gray-500')
                    with ui.row().classes('items-center gap-3'):
                        ui.label(f'{done}/{total or "?"}').classes('text-sm')
                        def remove_id(s=sid):
                            # Remove only from monitor list in config.json
                            current = list(config.get("monitor-series-id", []))
                            if s in current:
                                current = [x for x in current if x != s]
                                _save_monitor_ids(current)
                            optimistic_ids.discard(s)
                            ui.notify(f'Removed "{s}" from monitor list', color='warning')
                            render_queue.refresh()
                        ui.button('Remove', on_click=remove_id).props('outline dense')

    render_queue()
    ui.timer(2.0, render_queue.refresh)
