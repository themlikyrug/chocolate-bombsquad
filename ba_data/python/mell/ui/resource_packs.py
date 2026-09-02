"""UI for managing installed resource packs."""
from __future__ import annotations

from pathlib import Path
from mell.resource_packs import (
    get_pack_icon, 
    apply_resource_pack, 
    clear_resource_packs
)
import bascenev1 as bs
import babase as ba
import bauiv1 as bui
import textwrap
import threading

class ResourcePacksWarningWindow(bui.Window):
    """A window that tells the user resource 
    packs are experimental."""
    def __init__(self):
        transition = 'in_scale'
        width = 700
        height = 380
        super().__init__(
            root_widget=bui.containerwidget(
                size=(width, height),
                parent=bui.get_special_widget('overlay_stack'),
                toolbar_visibility="menu_minimal_no_back",
                scale=1.0,
                transition=transition,
                darken_behind=True,
            ),
        )
        button_spacing = 140
        button_width = 200
        button_height = 70
        button_y = 45
        v = height - 50
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, v),
            size=(0, 0),
            text=bui.Lstr(r="resourcePacksWarningText"),
            scale=1.15,
            maxwidth=width * 0.85,
            h_align="center",
            v_align="top",
        )
        v -= 170
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, v),
            size=(0, 0),
            text=bui.Lstr(r="warningContinueText"),
            color=(0.8, 0.8, 0.85),
            scale=1.1,
            maxwidth=width * 0.85,
            h_align="center",
            v_align="center",
        )
        btn = bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(button_spacing - (button_width * 0.5), button_y),
            size=(button_width, button_height),
            text_scale=1.1,
            label=bui.Lstr(r='backText'),
            on_activate_call=self.close,
        )
        bui.containerwidget(
            edit=self._root_widget,
            cancel_button=btn,
        )
        bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(width - button_spacing - (button_width * 0.5), button_y),
            size=(button_width, button_height),
            text_scale=1.1,
            label=bui.Lstr(r='continueText'),
            on_activate_call=self.agree,
        )
    
    def close(self):
        bui.containerwidget(
            edit=self._root_widget,
            transition='out_scale',
        )
    
    def agree(self):
        self.close()
        window = bui.app.ui_v1.get_main_window()
        window.main_window_replace(ResourcePacksWindow)

class ResourcePacksApplyingWindow(bui.Window):
    """Window informing the user all
    resource packs are currently being applied."""
    def __init__(
        self,
    ) -> None:
        self._width = 550
        self._height = 200
        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height),
                transition='in_scale',
                parent=bui.get_special_widget('overlay_stack'),
                darken_behind=True,
            )
        )
        spinner_size = 130
        spinner_spacing = 10
        connecting_text_y = self._height - 80
        text_maxwidth = self._width * 0.64
        text = bui.Lstr(r='applyingResourcePacksText')
        self._connecting_text = bui.textwidget(
            parent=self._root_widget,
            position=(
                self._width - 70 - (spinner_size - spinner_spacing), 
                connecting_text_y,
            ),
            size=(0, 0),
            scale=1.2,
            h_align='right',
            v_align='center',
            text=text,
            maxwidth=text_maxwidth,
        )

        self._spinner = bui.spinnerwidget(
            parent=self._root_widget,
            position=(self._width - 100, self._height * 0.54),
            size=spinner_size,
        )

        text = bui.Lstr(r='doNotQuitGameText')
        self._info_text = bui.textwidget(
            parent=self._root_widget,
            position=(
                self._width - 70 - (spinner_size - spinner_spacing), 
                connecting_text_y - 35,
            ),
            size=(0, 0),
            color=(0.6, 0.5, 0.6),
            flatness=1.0,
            shadow=0.0,
            scale=1.1,
            h_align='right',
            v_align='center',
            text=text,
            maxwidth=text_maxwidth,
        )

    def close(self) -> None:
        if not self._root_widget or self._root_widget.transitioning_out:
            return
        bui.containerwidget(
            edit=self._root_widget,
            transition=('out_scale'),
        )


class ResourcePacksWindow(bui.MainWindow):
    """Window for enabling and disabling installed resource packs."""

    WIDTH = 1300
    HEIGHT = 650
    SCALE = 0.9

    SCROLL_WIDTH = 500
    SCROLL_HEIGHT = 470
    SCROLL_BOTTOM = 50
    LIST_LABEL_GAP = 20

    PACK_BUTTON_HEIGHT = 180
    PACK_BUTTON_SPACING = 8
    PACK_BUTTON_COLOR = (0.45, 0.4, 0.55)
    PACK_BUTTON_ACTIVATED_COLOR = (0.7, 0.5, 0.85)

    PACK_NAME_COLOR = (1.0, 1.0, 1.0)
    PACK_NAME_SELECTED_COLOR = (1.0, 0.9, 0.6)
    PACK_DESC_COLOR = (0.75, 0.75, 0.8)

    MOVE_BUTTON_SIZE = 80
    MOVE_BUTTON_COLOR = (0.5, 0.45, 0.6)
    MOVE_BUTTON_DISABLED_COLOR = (0.3, 0.3, 0.35)

    def main_window_should_preserve_selection(self) -> bool:
        return False

    def __init__(
        self,
        transition: str = "in_scale",
        origin_widget: bui.Widget | None = None,
    ):
        self._all_packs = list(bui.app.resource_packs)
        self._enabled_packs: list = []
        self._pack_buttons: dict = {}
        self._pack_name_widgets: dict = {}
        self._selected_pack = None
        self._filter_text = ''

        self._select_sound = bui.getsound('click01')
        self._move_sound = bui.getsound('gunCocking')
        self._done_sound = bui.getsound('gunCocking')

        self._load_enabled_packs()

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self.WIDTH, self.HEIGHT),
                toolbar_visibility="menu_full_no_back",
                scale=self.SCALE,
            ),
            origin_widget=origin_widget,
            transition=transition,
        )
        self._applying_window = None
        self._saved_music = None

        self._create_header()
        self._create_pack_lists()
        self._create_move_buttons()

        self.rebuild()
        self._update_selection_state()

    def _load_enabled_packs(self) -> None:
        """Load the currently enabled packs from the config."""

        enabled_packs = bui.app.config.setdefault(
            "vt_enabled_packs",
            [],
        )

        self._enabled_packs = [
            pack
            for pack in self._all_packs
            if pack.namespace in enabled_packs
        ]

    def _create_header(self) -> None:
        """Create the title, subtitle, and top buttons."""

        bui.textwidget(
            parent=self._root_widget,
            position=(self.WIDTH * 0.5, self.HEIGHT - 45),
            size=(0, 0),
            text=bui.Lstr(resource="resourcePacksText"),
            color=bui.app.ui_v1.title_color,
            scale=1.3,
            maxwidth=500,
            h_align="center",
            v_align="center",
        )

        self._filter_widget = bui.textwidget(
            parent=self._root_widget,
            position=(self.WIDTH * 0.5 - 170, self.HEIGHT - 116),
            size=(340, 38),
            text='',
            editable=True,
            description=bui.Lstr(resource='filterText'),
            maxwidth=300,
            h_align='left',
            v_align='center',
            on_return_press_call=self._apply_filter,
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(self.WIDTH * 0.5 - 205, self.HEIGHT - 94),
            size=(0, 0),
            text=bui.Lstr(resource='filterText'),
            color=(0.7, 0.7, 0.75),
            scale=0.78,
            h_align='right',
            v_align='center',
        )

        self._selection_status = bui.textwidget(
            parent=self._root_widget,
            position=(self.WIDTH * 0.5, self.HEIGHT - 68),
            size=(0, 0),
            text="Select a pack below, then use the arrows to move it between lists.",
            color=(0.72, 0.72, 0.78),
            scale=0.75,
            maxwidth=700,
            h_align="center",
            v_align="center",
        )

        button_size = (60, 60)
        button_y = self.HEIGHT - 50 - (button_size[1] * 0.5)

        self._back_button = bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(30, button_y),
            size=button_size,
            textcolor=(1, 1, 1),
            text_scale=1.3,
            label=bui.charstr(bui.SpecialChar.BACK),
            button_type="backSmall",
            on_activate_call=self.main_window_back,
        )

        bui.containerwidget(
            edit=self._root_widget,
            cancel_button=self._back_button,
        )

        self._done_button = bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(
                self.WIDTH - 30 - button_size[0],
                button_y,
            ),
            button_type='square',
            color=(0.5, 0.7, 0.4),
            size=button_size,
            textcolor=(1, 1, 1),
            text_scale=1.3,
            label=bui.charstr(bui.SpecialChar.PLAY_BUTTON),
            on_activate_call=self._start_apply_thread,
        )

        bui.containerwidget(
            edit=self._root_widget,
            start_button=self._done_button,
        )

    def _create_pack_lists(self) -> None:
        """Create the enabled and disabled pack scroll areas, with labels."""

        # Keep the two lists centered around the move buttons.
        scroll_x = self.SCROLL_WIDTH - 180
        disabled_x = scroll_x - self.SCROLL_WIDTH * 0.5
        enabled_x = self.WIDTH - scroll_x - self.SCROLL_WIDTH * 0.5

        self._disabled_label = bui.textwidget(
            parent=self._root_widget,
            position=(
                disabled_x + self.SCROLL_WIDTH * 0.5,
                self.SCROLL_BOTTOM + self.SCROLL_HEIGHT + self.LIST_LABEL_GAP,
            ),
            size=(0, 0),
            scale=1.0,
            color=(0.8, 0.8, 0.85),
            h_align="center",
            v_align="center",
        )

        self._enabled_label = bui.textwidget(
            parent=self._root_widget,
            position=(
                enabled_x + self.SCROLL_WIDTH * 0.5,
                self.SCROLL_BOTTOM + self.SCROLL_HEIGHT + self.LIST_LABEL_GAP,
            ),
            size=(0, 0),
            scale=1.0,
            color=(0.75, 0.9, 0.75),
            h_align="center",
            v_align="center",
        )

        self._disabled_scroll_widget = self._create_scroll_widget(
            position=(disabled_x, self.SCROLL_BOTTOM)
        )

        self._disabled_container = self._create_scroll_container(
            self._disabled_scroll_widget
        )

        self._enabled_scroll_widget = self._create_scroll_widget(
            position=(enabled_x, self.SCROLL_BOTTOM)
        )

        self._enabled_container = self._create_scroll_container(
            self._enabled_scroll_widget
        )

    def _create_scroll_widget(
        self,
        position: tuple[float, float],
    ) -> bui.Widget:
        """Create one of the pack list scroll widgets."""

        return bui.scrollwidget(
            parent=self._root_widget,
            size=(self.SCROLL_WIDTH, self.SCROLL_HEIGHT),
            position=position,
            simple_culling_v=20.0,
            highlight=False,
            center_small_content_horizontally=True,
            selection_loops_to_parent=True,
            border_opacity=0.6,
        )

    def _create_scroll_container(
        self,
        parent: bui.Widget,
    ) -> bui.Widget:
        """Create the container used inside a scroll widget."""

        return bui.containerwidget(
            parent=parent,
            size=(self.SCROLL_WIDTH, 1),
            background=False,
            selection_loops_to_parent=True,
        )

    def _create_move_buttons(self) -> None:
        """Create the buttons used to move packs between lists."""

        size = (
            self.MOVE_BUTTON_SIZE,
            self.MOVE_BUTTON_SIZE,
        )

        center_x = 35 + self.WIDTH * 0.5 - (self.MOVE_BUTTON_SIZE * 0.5)
        y = self.HEIGHT * 0.5 - (self.MOVE_BUTTON_SIZE * 0.5)
        row_gap = 5
        col_gap = 5
        row_2_y = y - self.MOVE_BUTTON_SIZE - 30

        self._send_to_disabled_btn = bui.buttonwidget(
            parent=self._root_widget,
            label=bui.charstr(bui.SpecialChar.LEFT_ARROW),
            position=(center_x - self.MOVE_BUTTON_SIZE - col_gap, y),
            size=size,
            autoselect=False,
            text_scale=1.5,
            button_type='square',
            color=self.MOVE_BUTTON_COLOR,
            textcolor=(1, 1, 1),
            on_activate_call=bui.WeakCallPartial(self._send_to_disabled),
        )

        self._send_to_enabled_btn = bui.buttonwidget(
            parent=self._root_widget,
            label=bui.charstr(bui.SpecialChar.RIGHT_ARROW),
            position=(center_x + col_gap, y),
            size=size,
            autoselect=False,
            text_scale=1.5,
            button_type='square',
            color=self.MOVE_BUTTON_COLOR,
            textcolor=(1, 1, 1),
            on_activate_call=bui.WeakCallPartial(self._send_to_enabled),
        )

        self._move_up_btn = bui.buttonwidget(
            parent=self._root_widget,
            label=bui.charstr(bui.SpecialChar.UP_ARROW),
            position=(center_x - self.MOVE_BUTTON_SIZE - col_gap, row_2_y),
            size=size,
            autoselect=False,
            text_scale=1.5,
            button_type='square',
            color=self.MOVE_BUTTON_DISABLED_COLOR,
            textcolor=(1, 1, 1),
            on_activate_call=bui.WeakCallPartial(self._move_enabled_pack, -1),
        )

        self._move_down_btn = bui.buttonwidget(
            parent=self._root_widget,
            label=bui.charstr(bui.SpecialChar.DOWN_ARROW),
            position=(center_x + col_gap, row_2_y),
            size=size,
            autoselect=False,
            text_scale=1.5,
            button_type='square',
            color=self.MOVE_BUTTON_DISABLED_COLOR,
            textcolor=(1, 1, 1),
            on_activate_call=bui.WeakCallPartial(self._move_enabled_pack, 1),
        )

        bui.textwidget(
            parent=self._root_widget,
            position=(center_x - (self.MOVE_BUTTON_SIZE * 0.5) - col_gap, y - 16),
            size=(0, 0),
            text='Disable',
            color=(0.82, 0.72, 0.72),
            scale=0.74,
            h_align='center',
            v_align='center',
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(center_x + (self.MOVE_BUTTON_SIZE * 0.5) + col_gap, y - 16),
            size=(0, 0),
            text='Enable',
            color=(0.72, 0.82, 0.72),
            scale=0.74,
            h_align='center',
            v_align='center',
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(center_x - (self.MOVE_BUTTON_SIZE * 0.5) - col_gap, row_2_y - 16),
            size=(0, 0),
            text='Up',
            color=(0.82, 0.82, 0.75),
            scale=0.74,
            h_align='center',
            v_align='center',
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(center_x + (self.MOVE_BUTTON_SIZE * 0.5) + col_gap, row_2_y - 16),
            size=(0, 0),
            text='Down',
            color=(0.82, 0.82, 0.75),
            scale=0.74,
            h_align='center',
            v_align='center',
        )

    def _apply_filter(self) -> None:
        """Refresh the list using the current filter text."""
        if self._filter_widget is None:
            return
        self._filter_text = str(bui.textwidget(query=self._filter_widget)).strip().lower()
        self.rebuild()

    def _matches_filter(self, pack) -> bool:
        """Return whether a pack matches the current filter query."""
        if not self._filter_text:
            return True
        haystack = f'{pack.name} {pack.description}'.lower()
        return self._filter_text in haystack

    def _update_selection_state(self) -> None:
        """Refresh the current-selection status text and button states."""

        if self._selected_pack is None:
            text = 'Select a pack to enable, disable, or reorder it.'
            color = (0.7, 0.7, 0.78)
        else:
            text = f'Selected: {self._selected_pack.name}'
            color = (1.0, 0.9, 0.65)

        bui.textwidget(edit=self._selection_status, text=text, color=color)

        selected_enabled = (
            self._selected_pack is not None
            and self._selected_pack in self._enabled_packs
        )
        selected_disabled = (
            self._selected_pack is not None
            and self._selected_pack not in self._enabled_packs
        )

        if selected_enabled:
            current_index = self._enabled_packs.index(self._selected_pack)
            can_move_up = current_index > 0
            can_move_down = current_index < len(self._enabled_packs) - 1
        else:
            can_move_up = False
            can_move_down = False

        for btn, enabled in (
            (self._send_to_disabled_btn, selected_enabled),
            (self._send_to_enabled_btn, selected_disabled),
            (self._move_up_btn, can_move_up),
            (self._move_down_btn, can_move_down),
        ):
            bui.buttonwidget(
                edit=btn,
                color=(
                    self.MOVE_BUTTON_COLOR
                    if enabled
                    else self.MOVE_BUTTON_DISABLED_COLOR
                ),
            )

    def rebuild(self) -> None:
        """Rebuild both resource-pack lists."""

        self._clear_containers()

        disabled_packs = [
            pack
            for pack in self._all_packs
            if pack not in self._enabled_packs and self._matches_filter(pack)
        ]
        enabled_packs = [
            pack for pack in self._enabled_packs if self._matches_filter(pack)
        ]
        no_packs = bui.Lstr(r='noPacksAvailableText')
        nothing_enabled = bui.Lstr(r='nothingEnabledYetText')
        disabled_len_text = bui.Lstr(
            value='${A} (${B})',
            subs=[
                ('${A}', bui.Lstr(r='availableText')),
                ('${B}', str(len(disabled_packs))),
            ],
        )
        enabled_len_text = bui.Lstr(
            value='${A} (${B})',
            subs=[
                ('${A}', bui.Lstr(r='enabledText')),
                ('${B}', str(len(self._enabled_packs))),
            ],
        )

        self._rebuild_list(
            self._disabled_container,
            disabled_packs,
            empty_text=no_packs,
        )

        self._rebuild_list(
            self._enabled_container,
            enabled_packs,
            empty_text=nothing_enabled,
        )

        bui.textwidget(
            edit=self._disabled_label,
            text=disabled_len_text,
        )
        bui.textwidget(
            edit=self._enabled_label,
            text=enabled_len_text,
        )

        self._update_selection_state()

    def _clear_containers(self) -> None:
        """Delete all existing pack buttons."""

        for container in (
            self._disabled_container,
            self._enabled_container,
        ):
            for child in container.get_children():
                child.delete()

        self._pack_buttons.clear()
        self._pack_name_widgets.clear()

    def _rebuild_list(
        self,
        container: bui.Widget,
        packs: list,
        empty_text: str,
    ) -> None:
        """Populate one pack list."""

        height = self._get_list_height(len(packs))

        bui.containerwidget(
            edit=container,
            size=(self.SCROLL_WIDTH, height),
        )

        if not packs:
            bui.textwidget(
                parent=container,
                position=(self.SCROLL_WIDTH * 0.5, height * 0.5),
                size=(0, 0),
                text=empty_text,
                scale=0.9,
                color=(0.5, 0.5, 0.55),
                h_align="center",
                v_align="center",
            )
            return

        button_width = self.SCROLL_WIDTH - 10
        y = height

        for pack in packs:
            tex = get_pack_icon(pack, ui=True)
            is_selected = pack == self._selected_pack
            btn = bui.buttonwidget(
                parent=container,
                label='',
                position=(
                    (self.SCROLL_WIDTH - button_width) * 0.5,
                    y - self.PACK_BUTTON_HEIGHT,
                ),
                size=(
                    button_width,
                    self.PACK_BUTTON_HEIGHT,
                ),
                autoselect=False,
                enable_sound=False,
                color=(
                    self.PACK_BUTTON_ACTIVATED_COLOR
                    if is_selected
                    else self.PACK_BUTTON_COLOR
                ),
            )
            self._pack_buttons[pack] = btn
            avatar_size = 110
            bui.imagewidget(
                parent=container,
                texture=tex,
                position=(
                    20,
                    (y - (self.PACK_BUTTON_HEIGHT * 0.5)) - (avatar_size * 0.5),
                ),
                draw_controller=btn,
                size=(avatar_size, avatar_size),
            )
            name_widget = bui.textwidget(
                parent=container,
                position=(
                    avatar_size + 30,
                    y - 30,
                ),
                size=(0, 0),
                text=pack.name,
                scale=1.15,
                color=(
                    self.PACK_NAME_SELECTED_COLOR
                    if is_selected
                    else self.PACK_NAME_COLOR
                ),
                maxwidth=(button_width - avatar_size) - 45,
                draw_controller=btn,
                h_align="left",
                v_align="top",
            )
            self._pack_name_widgets[pack] = name_widget
            description = textwrap.fill(pack.description, 38)
            bui.textwidget(
                parent=container,
                position=(
                    avatar_size + 30,
                    y - 62,
                ),
                size=(0, 0),
                text=description,
                color=self.PACK_DESC_COLOR,
                scale=0.9,
                maxwidth=(button_width - avatar_size) - 45,
                max_height=self.PACK_BUTTON_HEIGHT - 80,
                draw_controller=btn,
                h_align="left",
                v_align="top",
            )
            bui.buttonwidget(
                edit=btn,
                on_activate_call=bui.WeakCallPartial(
                    self._select_pack,
                    pack,
                ),
            )

            y -= self.PACK_BUTTON_HEIGHT + self.PACK_BUTTON_SPACING

    def _get_list_height(self, pack_count: int) -> float:
        """Return the required height for a pack list."""

        if pack_count <= 0:
            return self.SCROLL_HEIGHT

        return (
            pack_count * self.PACK_BUTTON_HEIGHT
            + (pack_count - 1) * self.PACK_BUTTON_SPACING
        )

    def _select_pack(self, pack) -> None:
        """Select a resource pack."""
        self._select_sound.play()
        if pack == self._selected_pack:
            self._selected_pack = None
        else:
            self._selected_pack = pack

        for p, btn in self._pack_buttons.items():
            selected = p == self._selected_pack
            bui.buttonwidget(
                edit=btn,
                color=(
                    self.PACK_BUTTON_ACTIVATED_COLOR
                    if selected
                    else self.PACK_BUTTON_COLOR
                ),
            )
            name_widget = self._pack_name_widgets.get(p)
            if name_widget is not None:
                bui.textwidget(
                    edit=name_widget,
                    color=(
                        self.PACK_NAME_SELECTED_COLOR
                        if selected
                        else self.PACK_NAME_COLOR
                    ),
                )

        self._update_selection_state()

    def _send_to_enabled(self) -> None:
        """Enable the currently selected pack."""

        pack = self._selected_pack

        if pack is None:
            return

        if pack not in self._enabled_packs:
            self._enabled_packs.append(pack)
        self._move_sound.play()
        self.rebuild()
        self._update_selection_state()

    def _send_to_disabled(self) -> None:
        """Disable the currently selected pack."""

        pack = self._selected_pack

        if pack is None:
            return

        if pack in self._enabled_packs:
            self._enabled_packs.remove(pack)
        self._move_sound.play()
        self.rebuild()
        self._update_selection_state()
    
    def _move_enabled_pack(self, direction: int) -> None:
        """Move the currently selected enabled pack up or down in priority."""
        pack = self._selected_pack
        if pack is None or pack not in self._enabled_packs:
            return

        index = self._enabled_packs.index(pack)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._enabled_packs):
            return

        self._enabled_packs[index], self._enabled_packs[new_index] = (
            self._enabled_packs[new_index],
            self._enabled_packs[index],
        )
        self._move_sound.play()
        self.rebuild()
        self._update_selection_state()

    def _start_apply_thread(self):
        self._applying_window = ResourcePacksApplyingWindow()
        # ok, so music playing is bad so lets kill it for now
        activity = bs.get_foreground_host_activity()
        globs = activity.globalsnode
        # uuuggghhh
        for type in bs.MusicType:
            if type.value == globs.music:
                self._saved_music = type
        with activity.context:
            bs.setmusic(None)
        threading.Thread(
            target=self._apply_resource_packs_thread,
            daemon=False,
        ).start()
    
    def _apply_resource_packs_thread(self):
        """Apply the current resource-pack configuration."""
        config = bui.app.config.setdefault(
            "vt_enabled_packs",
            [],
        )

        config.clear()
        try:
            clear_resource_packs()
        except Exception as exc:
            bui.pushcall(
                bui.WeakCall(self._on_done, False),
                from_other_thread=True,
            )
            error_text = bui.Lstr(
                resource='failedToApplyResourcePack',
                subs=[
                    ('${ERROR}', str(exc)),
                ],
            )
            bui.screenmessage(error_text, color=(1, 0, 0))
            bui.getsound('error').play()
            return
        for pack in self._enabled_packs:
            try:
                apply_resource_pack(pack)
                config.append(str(pack.namespace))
            except Exception as exc:
                bui.pushcall(
                    bui.WeakCall(self._on_done, False),
                    from_other_thread=True,
                )
                error_text = bui.Lstr(
                    resource='failedToApplyResourcePack',
                    subs=[
                        ('${ERROR}', str(exc)),
                    ],
                )
                bui.screenmessage(error_text, color=(1, 0, 0))
                bui.pushcall(bui.getsound('error').play)
                return
        bui.pushcall(
            self._on_done,
            from_other_thread=True,
        )

    def _on_done(self, success: bool = True) -> None:
        if self._applying_window:
            self._applying_window.close()
            self._applying_window = None
        # alright, let it free again
        with bs.get_foreground_host_activity().context:
            bs.setmusic(self._saved_music)
        if success:
            self._done_sound.play()
        bui.app.config.commit()
        if success:
            bui.screenmessage(bui.Lstr(r="mustRestartText"), color=(1, 1, 0))
        self.main_window_back()