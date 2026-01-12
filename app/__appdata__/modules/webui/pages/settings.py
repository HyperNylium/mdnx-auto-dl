from nicegui import run, ui
from nicegui.events import ValueChangeEventArguments


def settings_page() -> None:
    with ui.tabs().props('align="center"').classes('w-full') as tabs:
        servauth_tab = ui.tab('Service auth')
        conf_tab = ui.tab('Configuration')
        mdnxsettings_tab = ui.tab('MDNX Settings')

    with ui.tab_panels(tabs, value=servauth_tab).classes('w-full flex-1 min-h-0'):

        # Service Auth Tab
        with ui.tab_panel(servauth_tab).classes('w-full h-full min-h-0'):
            with ui.column().classes('w-full h-full'):

                service_dropdown = ui.select(
                    options=['Crunchyroll', 'HiDive'],
                    value='Crunchyroll',
                    label='Service',
                ).classes('w-full')

                with ui.column().classes('w-full') as switch_container:
                    pass

                ui.separator().classes('w-full q-my-md')

                with ui.column().classes('w-full flex-1 items-center justify-start q-pt-sm') as form_container:
                    pass

                loading_dialog = ui.dialog().props('persistent transition-show="fade" transition-hide="fade"')
                with loading_dialog:
                    with ui.card().classes('q-pa-lg'):
                        with ui.column().classes('items-center'):
                            ui.spinner(size='lg')
                            ui.label('Loading...')

                # Crunchyroll
                with switch_container:
                    def on_crunchyroll_enabled_change(e: ValueChangeEventArguments):
                        crunchyroll_form.set_visibility(bool(e.value))
                        # TODO: will save "CR_ENABLED" config here

                    crunchyroll_enabled = ui.switch(
                        'Crunchyroll enabled?',
                        value=False,  # TODO: load "CR_ENABLED" state from config
                        on_change=on_crunchyroll_enabled_change,
                    )

                with form_container:
                    with ui.column().classes('w-full max-w-xl') as crunchyroll_form:
                        crunchyroll_username_input = ui.input('Username').classes('w-full')
                        crunchyroll_password_input = ui.input('Password').props('type=password').classes('w-full')

                        with ui.row().classes('w-full justify-end q-mt-md'):
                            crunchyroll_auth_button = ui.button('Auth').classes('w-full')

                        crunchyroll_reset_button = ui.button('Reset creds').classes('w-full q-mt-sm')

                    crunchyroll_form.set_visibility(False)

                    def update_crunchyroll_auth_button_state():
                        username = (crunchyroll_username_input.value or '').strip()
                        password = (crunchyroll_password_input.value or '').strip()
                        if username == '' or password == '':
                            crunchyroll_auth_button.disable()
                        else:
                            crunchyroll_auth_button.enable()

                    def on_crunchyroll_username_change(e: ValueChangeEventArguments):
                        update_crunchyroll_auth_button_state()

                    def on_crunchyroll_password_change(e: ValueChangeEventArguments):
                        update_crunchyroll_auth_button_state()

                    crunchyroll_username_input.on_value_change(on_crunchyroll_username_change)
                    crunchyroll_password_input.on_value_change(on_crunchyroll_password_change)

                    update_crunchyroll_auth_button_state()

                    async def on_crunchyroll_auth_click():
                        crunchyroll_username_input.disable()
                        crunchyroll_password_input.disable()
                        crunchyroll_auth_button.disable()
                        crunchyroll_reset_button.disable()

                        loading_dialog.open()

                        ok = await run.io_bound(
                            auth_crunchyroll,
                            crunchyroll_username_input.value,
                            crunchyroll_password_input.value,
                        )

                        loading_dialog.close()

                        crunchyroll_username_input.enable()
                        crunchyroll_password_input.enable()
                        crunchyroll_reset_button.enable()
                        update_crunchyroll_auth_button_state()

                        if ok:
                            ui.notify('Authed with Crunchyroll', type='positive')
                        else:
                            ui.notify('Crunchyroll auth failed', type='negative')

                    crunchyroll_auth_button.on('click', on_crunchyroll_auth_click)

                    async def on_crunchyroll_reset_click():
                        crunchyroll_username_input.disable()
                        crunchyroll_password_input.disable()
                        crunchyroll_auth_button.disable()
                        crunchyroll_reset_button.disable()

                        loading_dialog.open()

                        ok = await run.io_bound(reset_crunchyroll_creds)

                        loading_dialog.close()

                        crunchyroll_username_input.enable()
                        crunchyroll_password_input.enable()
                        crunchyroll_reset_button.enable()

                        crunchyroll_username_input.set_value('')
                        crunchyroll_password_input.set_value('')
                        update_crunchyroll_auth_button_state()

                        if ok:
                            ui.notify('Reset Crunchyroll creds', type='positive')
                        else:
                            ui.notify('Crunchyroll reset failed', type='negative')

                    crunchyroll_reset_button.on('click', on_crunchyroll_reset_click)

                # HiDive
                with switch_container:
                    def on_hidive_enabled_change(e: ValueChangeEventArguments):
                        hidive_form.set_visibility(bool(e.value))
                        # TODO: will save "HIDIVE_ENABLED" config here

                    hidive_enabled = ui.switch(
                        'HiDive enabled?',
                        value=False,  # TODO: load "HIDIVE_ENABLED" state from config
                        on_change=on_hidive_enabled_change,
                    )

                with form_container:
                    with ui.column().classes('w-full max-w-xl') as hidive_form:
                        hidive_username_input = ui.input('Username').classes('w-full')
                        hidive_password_input = ui.input('Password').props('type=password').classes('w-full')

                        with ui.row().classes('w-full justify-end q-mt-md'):
                            hidive_auth_button = ui.button('Auth').classes('w-full')

                        hidive_reset_button = ui.button('Reset creds').classes('w-full q-mt-sm')

                    hidive_form.set_visibility(False)

                    def update_hidive_auth_button_state():
                        username = (hidive_username_input.value or '').strip()
                        password = (hidive_password_input.value or '').strip()
                        if username == '' or password == '':
                            hidive_auth_button.disable()
                        else:
                            hidive_auth_button.enable()

                    def on_hidive_username_change(e: ValueChangeEventArguments):
                        update_hidive_auth_button_state()

                    def on_hidive_password_change(e: ValueChangeEventArguments):
                        update_hidive_auth_button_state()

                    hidive_username_input.on_value_change(on_hidive_username_change)
                    hidive_password_input.on_value_change(on_hidive_password_change)

                    update_hidive_auth_button_state()

                    async def on_hidive_auth_click():
                        hidive_username_input.disable()
                        hidive_password_input.disable()
                        hidive_auth_button.disable()
                        hidive_reset_button.disable()

                        loading_dialog.open()

                        ok = await run.io_bound(
                            auth_hidive,
                            hidive_username_input.value,
                            hidive_password_input.value,
                        )

                        loading_dialog.close()

                        hidive_username_input.enable()
                        hidive_password_input.enable()
                        hidive_reset_button.enable()
                        update_hidive_auth_button_state()

                        if ok:
                            ui.notify('Authed with HiDive', type='positive')
                        else:
                            ui.notify('HiDive auth failed', type='negative')

                    hidive_auth_button.on('click', on_hidive_auth_click)

                    async def on_hidive_reset_click():
                        hidive_username_input.disable()
                        hidive_password_input.disable()
                        hidive_auth_button.disable()
                        hidive_reset_button.disable()

                        loading_dialog.open()

                        ok = await run.io_bound(reset_hidive_creds)

                        loading_dialog.close()

                        hidive_username_input.enable()
                        hidive_password_input.enable()
                        hidive_reset_button.enable()

                        hidive_username_input.set_value('')
                        hidive_password_input.set_value('')
                        update_hidive_auth_button_state()

                        if ok:
                            ui.notify('Reset HiDive creds', type='positive')
                        else:
                            ui.notify('HiDive reset failed', type='negative')

                    hidive_reset_button.on('click', on_hidive_reset_click)

                def set_service_visibility(service_name):
                    crunchyroll_enabled.set_visibility(service_name == 'Crunchyroll')
                    crunchyroll_form.set_visibility(service_name == 'Crunchyroll' and crunchyroll_enabled.value)

                    hidive_enabled.set_visibility(service_name == 'HiDive')
                    hidive_form.set_visibility(service_name == 'HiDive' and hidive_enabled.value)

                set_service_visibility(service_dropdown.value)

                def on_service_change(e: ValueChangeEventArguments):
                    set_service_visibility(e.value)

                service_dropdown.on_value_change(on_service_change)

        # Configuration Tab
        with ui.tab_panel(conf_tab).classes('w-full h-full'):
            ui.label('Second tab').classes('w-full h-full flex items-center justify-center')

        # MDNX Settings Tab
        with ui.tab_panel(mdnxsettings_tab).classes('w-full h-full'):
            ui.label('Third tab').classes('w-full h-full flex items-center justify-center')


def auth_crunchyroll(username, password):
    import time
    time.sleep(1)
    return True


def auth_hidive(username, password):
    import time
    time.sleep(1)
    return True


def reset_crunchyroll_creds():
    import time
    time.sleep(1)
    return True


def reset_hidive_creds():
    import time
    time.sleep(1)
    return True
