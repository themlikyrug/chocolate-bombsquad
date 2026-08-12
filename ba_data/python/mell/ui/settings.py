# Released under the MIT License. See LICENSE for details.
#
"""UI for setting... settings."""
from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, override, Any
import logging

import bauiv1 as bui
import bascenev1 as bs
import os
import babase
import random
from bauiv1lib.popup import PopupMenu

if TYPE_CHECKING:
    from typing import Callable

class VTSettingsWindow(bui.MainWindow):
    """Window for selecting Vanilla Tweaks settings."""
    @override
    def main_window_should_preserve_selection(self) -> bool:
        return False
    
    def __init__(
        self,
        transition: str | None = 'in_right',
        origin_widget: bui.Widget | None = None,
    ):
        # pylint: disable=too-many-locals
        assert bui.app.classic is not None
        uiscale = bui.app.ui_v1.uiscale
        width = 1000 if uiscale is bui.UIScale.SMALL else 650
        height = 750 if uiscale is bui.UIScale.SMALL else 400

        uiscale = bui.app.ui_v1.uiscale
        # Do some fancy math to fill all available screen area up to the
        # size of our backing container. This lets us fit to the exact
        # screen shape at small ui scale.
        screensize = bui.get_virtual_screen_size()
        safesize = bui.get_virtual_safe_area_size()

        # We're a generally widescreen shaped window, so bump our
        # overall scale up a bit when screen width is wider than safe
        # bounds to take advantage of the extra space.
        smallscale = min(2.0, 1.5 * screensize[0] / safesize[0])
        scale = (
            smallscale
            if uiscale is bui.UIScale.SMALL
            else 1.3 if uiscale is bui.UIScale.MEDIUM else 1.1
        )
        target_height = min(height - 70, screensize[1] / scale)
        target_width = min(width - 80, screensize[0] / scale)
        yoffs = 0.5 * height + 0.5 * target_height + 30.0
        self._scroll_width = target_width - 30
        self._scroll_height = target_height - 45
        self._sub_width = min(500, self._scroll_width * 0.95)
        self._sub_height = 50
        settings = self.get_settings()
        # for every setting here, we add 50 to the
        # height of the sub widget
        for setting in settings:
            self._sub_height += 50
        start_y = self._sub_height - 60
        spacing = 2
        scroll_bottom = yoffs - 56 - self._scroll_height
        self._col_x = width * 0.12
        if uiscale is bui.UIScale.SMALL:
            self._col_x -= 40
        self.is_small = bui.app.ui_v1.uiscale is bui.UIScale.SMALL
        self.reset_clicks = 0
        
        super().__init__(
            root_widget=bui.containerwidget(
                size=(width, height),
                toolbar_visibility=(
                    'menu_minimal'
                    if uiscale is bui.UIScale.SMALL
                    else 'menu_full'
                ),
                scale=scale,
            ),
            transition=transition,
            origin_widget=origin_widget,
            # We're affected by screen size only at small ui-scale.
            refresh_on_screen_size_changes=uiscale is bui.UIScale.SMALL,
        )
        if uiscale is bui.UIScale.SMALL:
            self._back_button = None
            bui.containerwidget(
                edit=self._root_widget, on_cancel_call=self.main_window_back
            )
        else:
            self._back_button = btn = bui.buttonwidget(
                parent=self._root_widget,
                autoselect=True,
                position=(50, yoffs - 50.0),
                size=(70, 70),
                scale=0.8,
                text_scale=1.2,
                label=bui.charstr(bui.SpecialChar.BACK),
                button_type='backSmall',
                on_activate_call=self.main_window_back,
            )
            
            bui.containerwidget(edit=self._root_widget, cancel_button=btn)
        self._scrollwidget = bui.scrollwidget(
            parent=self._root_widget,
            size=(self._scroll_width, self._scroll_height),
            position=(
                width * 0.5 - self._scroll_width * 0.5,
                scroll_bottom,
            ),
            simple_culling_v=20.0,
            highlight=False,
            center_small_content_horizontally=True,
            selection_loops_to_parent=True,
            border_opacity=0.4,
        )
        bui.widget(edit=self._scrollwidget, right_widget=self._scrollwidget)
        self._subcontainer = bui.containerwidget(
            parent=self._scrollwidget,
            size=(self._sub_width, self._sub_height),
            background=False,
            selection_loops_to_parent=True,
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(0, yoffs - (55 if uiscale is bui.UIScale.SMALL else 35)),
            size=(width, 25),
            text=bui.Lstr(resource=f'vanillaTweaksText'),
            color=bui.app.ui_v1.title_color,
            h_align='center',
            v_align='center',
            scale=1.0,
            maxwidth=4000,
        )
        row_height = 50
        # dicts containing options
        self._buttons = {}
        self._multi_buttons_label = {}
        self._multi_buttons_buttons = {}
        self._popup_labels = {}
        self._popup_menus = {}
        self._checkboxes = {}
        self._labels = {}

        for row, setting in enumerate(settings):
            y = start_y - row * row_height

            if setting["type"] == "checkbox":
                self._build_checkbox(setting, y)

            elif setting["type"] == "popup":
                self._build_popup(setting, y)

            elif setting["type"] == "button":
                self._build_button(setting, y)

            elif setting["type"] == "multi_button":
                self._build_multi_button(setting, y)
            
            elif setting["type"] == "label":
                self._build_label(setting, y)
                
            else:
                pass

    def _build_checkbox(self, setting: dict, y: float):
        key = setting.get('key')
        lkey = setting.get('label')
        sound = setting.get('sound')
        info = setting.get('info')
        sub_option = setting.get('sub_option')
        x = self._col_x
        if sub_option:
            bui.imagewidget(
                parent=self._subcontainer,
                position=(x - 5, y - 3),
                size=(40, 45),
                texture=bui.gettexture('subOption'),
                color=(0.49, 0.45, 0.61),
            )
            x += 50
        self._checkboxes[lkey] = bui.checkboxwidget(
            parent=self._subcontainer,
            position=(x, y),
            size=(220, 40),
            autoselect=False,
            maxwidth=300,
            textcolor=(1.0, 1.0, 1.0),
            value=bui.app.config.get(key, False),
            text=bui.Lstr(resource=lkey),
            on_value_change_call=bui.Call(
                self._set_config, key, 
                sound=sound
            ),
        )
        if info:
            bui.buttonwidget(
                parent=self._subcontainer,
                position=(x + 360, y + 5),
                size=(60, 45),
                scale=0.75,
                label='?',
                text_scale=1.5,
                on_activate_call=bui.Call(
                    bui.screenmessage,
                    bui.Lstr(r=info)
                ),
            )
    
    def _build_button(self, setting: dict, y: float):
        label = setting.get('label')
        callback = setting.get('callback')
        size = (350, 50)
        self._buttons[label] = bui.buttonwidget(
            parent=self._subcontainer,
            position=(self._col_x, y),
            size=size,
            text_scale=1.0,
            label=bui.Lstr(resource=label),
            on_activate_call=callback,
        )
    
    def _build_label(self, setting: dict, y: float):
        text = setting.get('text')
        self._labels[text] = bui.textwidget(
            parent=self._subcontainer,
            position=(self._col_x, y + 25),
            text=bui.Lstr(resource=text),
            size=(0, 0),
            scale=0.85,
            h_align='left',
            v_align='center',
            maxwidth=500,
        )
    
    def _build_multi_button(self, setting: dict, y: float):
        xoffset = 70
        label = setting.get('label')

        self._multi_buttons_label[label] = bui.textwidget(
            parent=self._subcontainer,
            position=(self._col_x - xoffset, y + 25),
            text=bui.Lstr(resource=label),
            size=(0, 0),
            scale=0.8,
            h_align='left',
            v_align='center',
        )

        buttons = setting["buttons"]

        for i, btn in enumerate(buttons):
            label = btn["label"]
            key = btn["key"]

            self._multi_buttons_buttons[key] = bui.buttonwidget(
                parent=self._subcontainer,
                position=(self._col_x + 160 + (i * 160), y),
                size=(150, 50),
                label=label,
                on_activate_call=btn.get("callback"),
            )
    
    def _build_popup(self, setting: dict, y: float):
        xoffset = 70
        x = self._col_x
        callback = setting.get('callback')
        cdisp = setting.get('display')
        c = setting.get('choices')
        cur = setting.get('current')
        label = setting.get('label')
        sub_option = setting.get('sub_option')
        x_extra = 280
        if sub_option:
            bui.imagewidget(
                parent=self._subcontainer,
                position=(x - 5, y - 3),
                size=(40, 45),
                texture=bui.gettexture('subOption'),
                color=(0.49, 0.45, 0.61),
            )
            x += 120
            x_extra = 140
            y -= 5
        self._popup_labels[label] = bui.textwidget(
            parent=self._subcontainer,
            position=(x - xoffset, y + 25),
            text=bui.Lstr(resource=label),
            size=(0, 0),
            scale=0.9,
            h_align='left',
            v_align='center',
            maxwidth=x_extra - 30,
        )
        self._popup_menus[label] = PopupMenu(
            parent=self._subcontainer,
            position=(x + x_extra - xoffset, y),
            width=250,
            autoselect=False,
            on_value_change_call=callback,
            choices=c,
            choices_display=cdisp,
            button_size=(200, 50),
            current_choice=cur,
        )
        
    def _menu_type_choice(self, choice):
        key = "squda_entitychance"
        cfg = bui.app.config
        cfg[key] = choice
        cfg.apply_and_commit()

    def _set_config(self, 
        key: str, 
        val: Any, 
        sound: list | None = None
    ) -> None:
        cfg = bui.app.config
        cfg[key] = val
        cfg.apply_and_commit()
    
    def _open_resource_packs(self):
        show_warning = True
        if show_warning:
            from mell.ui.resource_packs import ResourcePacksWarningWindow
            ResourcePacksWarningWindow()
        else:
            from mell.ui.resource_packs import ResourcePacksWindow
            self.main_window_replace(ResourcePacksWindow)
            
    @override
    def get_main_window_state(self) -> bui.MainWindowState:
        # Support recreating our window for back/refresh purposes.
        cls = type(self)
        return bui.BasicMainWindowState(
            create_call=lambda transition, origin_widget: cls(
                transition=transition, origin_widget=origin_widget
            )
        )
    
    def get_settings(self):
        menu_choices = ['normal', 'the_pad_accurate', 'random']
        menu_choices_display = [
            bui.Lstr(r=f'menuTypes.{i}')
            for i in menu_choices
        ]
        settings = [
            {
                'type': 'button',
                'label': 'resourcePacksText',
                'callback': bui.WeakCallPartial(self._open_resource_packs),
            },
            {
                "type": "popup",
                "label": "menuTypesText",
                "choices": menu_choices,
                "display": menu_choices_display,
                "current": bui.app.config.setdefault("vt_menutype", "normal"),
                "callback": bui.WeakCallPartial(self._set_config, 'vt_menutype'),
            },
        ]
        return settings