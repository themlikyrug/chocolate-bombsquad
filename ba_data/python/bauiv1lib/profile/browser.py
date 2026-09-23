# Released under the MIT License. See LICENSE for details.
#
"""UI functionality related to browsing player profiles."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import bauiv1 as bui
import bascenev1 as bs

if TYPE_CHECKING:
    from typing import Any, ClassVar

class NewProfileWindow(bui.Window):
    """A window asking the user if they want to 
    clone the selected profile or start from scratch."""
    def __init__(self, profile_name: str | None = None):
        # pylint: disable=too-many-locals
        from bauiv1lib.profile.edit import EditProfileWindow
        self._profile_name = profile_name
        uiscale = bui.app.ui_v1.uiscale
        width = 400.0 if uiscale is bui.UIScale.SMALL else 350.0
        height = 200.0 if uiscale is bui.UIScale.SMALL else 180.0
        super().__init__(
            root_widget=bui.containerwidget(
                size=(width, height),
                transition='in_scale',
                scale=(
                    2.7
                    if uiscale is bui.UIScale.SMALL
                    else 1.7 if uiscale is bui.UIScale.MEDIUM else 1.3
                ),
                darken_behind=True,
                on_outside_click_call=self.close,
            )
        )
        self._back_button = btn = bui.buttonwidget(
            parent=self._root_widget,
            position=(20, height - 45),
            size=(64, 64),
            scale=0.7,
            autoselect=True,
            texture=bui.gettexture('nub'),
            label=bui.charstr(bui.SpecialChar.CLOSE),
            on_activate_call=self.close,
            color=(0.6, 0.2, 0.2),
            textcolor=(1, 1, 1),
        )
        bui.containerwidget(
            edit=self._root_widget, 
            cancel_button=btn
        )
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, height - 30),
            size=(0, 0),
            text=bui.Lstr(resource='newProfileWindow.titleText'),
            color=bui.app.ui_v1.title_color,
            maxwidth=width * 0.9,
            scale=0.7,
            h_align='center',
            v_align='center',
        )
        # text asking the player whether they're 
        # gonna clone or start from scratch
        brightness = 1.2
        # Wow. Okay.
        import bascenev1 as bs
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, height - 70),
            size=(0, 0),
            text=bui.Lstr(resource='newProfileWindow.queryText'),
            color=bs.Vec3(bui.app.ui_v1.title_color) * brightness,
            maxwidth=width * 0.9,
            scale=0.8,
            h_align='center',
            v_align='center',
        )
        textscale = 0.6
        button_width = 140
        button_spacing = 15
        button_amount = 2
        total_button_width = button_amount * button_width + (button_amount - 1) * button_spacing
        bui.buttonwidget(
            parent=self._root_widget,
            position=(
                width * 0.5 - total_button_width * 0.5, 
                20
            ),
            size=(button_width, 50),
            label=bui.Lstr(resource='newProfileWindow.cloneButtonText'),
            text_scale=textscale,
            on_activate_call=lambda: self._do_new(clone=True),
        )
        bui.buttonwidget(
            parent=self._root_widget,
            position=(
                width * 0.5 - total_button_width * 0.5 + button_width + button_spacing, 
                20
            ),
            size=(button_width, 50),
            label=bui.Lstr(resource='newProfileWindow.scratchButtonText'),
            text_scale=textscale,
            on_activate_call=lambda: self._do_new(clone=False),
        )

    def close(self):
        bui.containerwidget(
            edit=self._root_widget, 
            transition='out_scale'
        )

    def _do_new(self, clone: bool) -> None:
        from bauiv1lib.profile.edit import EditProfileWindow
        profile = None
        if clone:
            profile = self._profile_name
        self.close()
        window = bui.app.ui_v1.get_main_window()
        window.main_window_replace(
            lambda: EditProfileWindow(
                existing_profile=profile, 
                clone=clone
            )
        )

class ProfileBrowserWindow(bui.MainWindow):
    """Window for browsing player profiles."""

    # Keep track of this at the class level to share between instances.
    selected_profile: ClassVar[str | None] = None

    def __init__(
        self,
        transition: str | None = 'in_right',
        selected_profile: str | None = None,
        origin_widget: bui.Widget | None = None,
        minimal_toolbar: bool = False,
    ):
        self._minimal_toolbar = minimal_toolbar
        back_label = bui.Lstr(resource='backText')
        assert bui.app.classic is not None
        uiscale = bui.app.ui_v1.uiscale
        self._width = 800.0 if uiscale is bui.UIScale.SMALL else 600.0
        x_inset = 100.0 if uiscale is bui.UIScale.SMALL else 0.0
        self._height = (
            360.0
            if uiscale is bui.UIScale.SMALL
            else 385.0 if uiscale is bui.UIScale.MEDIUM else 410.0
        )

        # Need to handle out-transitions ourself for modal mode.
        if origin_widget is not None:
            self._transition_out = 'out_scale'
        else:
            self._transition_out = 'out_right'

        self._r = 'playerProfilesWindow'

        # Ensure we've got an account-profile in cases where we're signed in.
        assert bui.app.classic is not None
        bui.app.classic.accounts.ensure_have_account_player_profile()

        top_extra = 20 if uiscale is bui.UIScale.SMALL else 0

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height + top_extra),
                toolbar_visibility=(
                    'menu_minimal'
                    if (uiscale is bui.UIScale.SMALL or minimal_toolbar)
                    else 'menu_full'
                ),
                scale=(
                    2.5
                    if uiscale is bui.UIScale.SMALL
                    else 1.5 if uiscale is bui.UIScale.MEDIUM else 1.0
                ),
                stack_offset=(
                    (0, -14) if uiscale is bui.UIScale.SMALL else (0, 0)
                ),
            ),
            transition=transition,
            origin_widget=origin_widget,
        )

        if bui.app.ui_v1.uiscale is bui.UIScale.SMALL:
            self._back_button = bui.get_special_widget('back_button')
            bui.containerwidget(
                edit=self._root_widget, on_cancel_call=self.main_window_back
            )
        else:
            self._back_button = btn = bui.buttonwidget(
                parent=self._root_widget,
                id=f'{self.main_window_id_prefix}|back',
                position=(40 + x_inset, self._height - 59),
                size=(120, 60),
                scale=0.8,
                label=back_label,
                button_type='back',
                autoselect=True,
                on_activate_call=self.main_window_back,
            )
            bui.containerwidget(edit=self._root_widget, cancel_button=btn)
            bui.buttonwidget(
                edit=btn,
                button_type='backSmall',
                size=(60, 60),
                label=bui.charstr(bui.SpecialChar.BACK),
            )

        bui.textwidget(
            parent=self._root_widget,
            position=(self._width * 0.5, self._height - 36),
            size=(0, 0),
            text=bui.Lstr(resource=f'{self._r}.titleText'),
            maxwidth=300,
            color=bui.app.ui_v1.title_color,
            scale=0.9,
            h_align='center',
            v_align='center',
        )

        scroll_height = self._height - 140.0
        self._scroll_width = self._width - 60
        b_color = (0.6, 0.53, 0.63)
        button_size = 40
        v = (self._height - 30) - (button_size * 0.5)
        h = (self._width - 50) - (button_size * 0.5)
        if uiscale is bui.UIScale.SMALL:
            h -= 165
            v -= 15
            self._scroll_width -= 50
        
        self._new_button = bui.buttonwidget(
            parent=self._root_widget,
            id=f'{self.main_window_id_prefix}|new',
            position=(h, v),
            size=(button_size, button_size),
            on_activate_call=self._new_profile,
            color=b_color,
            button_type='square',
            autoselect=True,
            textcolor=(0.75, 0.7, 0.8),
            iconscale=1.2,
            icon=bui.gettexture('cuteSpaz'),
        )
        h -= button_size + 10
        self._edit_button = bui.buttonwidget(
            parent=self._root_widget,
            id=f'{self.main_window_id_prefix}|edit',
            position=(h, v),
            size=(button_size, button_size),
            on_activate_call=self._edit_profile,
            color=b_color,
            button_type='square',
            autoselect=True,
            textcolor=(0.75, 0.7, 0.8),
            iconscale=1.2,
            icon=bui.gettexture('startButton'),
        )
        v = self._height - 87

        bui.textwidget(
            parent=self._root_widget,
            position=(self._width * 0.5, self._height - 71),
            size=(0, 0),
            text=bui.Lstr(resource=f'{self._r}.explanationText'),
            color=bui.app.ui_v1.infotextcolor,
            maxwidth=self._width * 0.83,
            scale=0.6,
            h_align='center',
            v_align='center',
        )

        self._scrollwidget = bui.scrollwidget(
            parent=self._root_widget,
            highlight=False,
            position=(
                ((self._width * 0.5) + x_inset) - (self._scroll_width * 0.5), 
                v - scroll_height
            ),
            size=(self._scroll_width, scroll_height),
        )
        bui.widget(
            edit=self._scrollwidget,
            autoselect=True,
            left_widget=self._new_button,
        )
        bui.containerwidget(
            edit=self._root_widget, selected_child=self._scrollwidget
        )
        self._subcontainer = bui.containerwidget(
            parent=self._scrollwidget,
            size=(self._scroll_width, 32),
            background=False,
        )
        v -= 255
        self._profiles: dict[str, dict[str, Any]] | None = None
        if selected_profile is not None:
            type(self).selected_profile = selected_profile
        self._profile_widgets: list[bui.Widget] = []
        self._refresh()

    @override
    def get_main_window_state(self) -> bui.MainWindowState:
        # Support recreating our window for back/refresh purposes.
        cls = type(self)

        minimal_toolbar = self._minimal_toolbar

        return bui.BasicMainWindowState(
            create_call=lambda transition, origin_widget: cls(
                transition=transition,
                origin_widget=origin_widget,
                minimal_toolbar=minimal_toolbar,
            )
        )

    @override
    def main_window_should_preserve_selection(self) -> bool:
        return True

    # @override
    # def main_window_do_save_shared_state(self, state: dict) -> None:
    #     state['selected_profile'] = self._selected_profile

    # @override
    # def main_window_do_restore_shared_state(self, state: dict) -> None:
    #     pval = state.get('selected_profile')
    #     if isinstance(pval, str | None):
    #         print('RESTORING', pval)
    #         self._selected_profile = pval

    def _new_profile(self) -> None:
        # Clamp at 100 profiles (otherwise the server will and that's less
        # elegant looking).
        if len(self._profiles) > 100:
            bui.screenmessage(
                bui.Lstr(
                    translate=(
                        'serverResponses',
                        'Max number of profiles reached.',
                    )
                ),
                color=(1, 0, 0),
            )
            bui.getsound('error').play()
            return
        NewProfileWindow(
            profile_name=type(self).selected_profile,
        )


    def _delete_profile(self) -> None:
        # pylint: disable=cyclic-import
        from bauiv1lib import confirm

        if self.selected_profile is None:
            bui.getsound('error').play()
            bui.screenmessage(
                bui.Lstr(resource='nothingIsSelectedErrorText'), color=(1, 0, 0)
            )
            return
        if self.selected_profile == '__account__':
            bui.getsound('error').play()
            bui.screenmessage(
                bui.Lstr(resource=f'{self._r}.cantDeleteAccountProfileText'),
                color=(1, 0, 0),
            )
            return
        confirm.ConfirmWindow(
            bui.Lstr(
                resource=f'{self._r}.deleteConfirmText',
                subs=[('${PROFILE}', self.selected_profile)],
            ),
            self._do_delete_profile,
            width=350,
        )

    def _do_delete_profile(self) -> None:
        plus = bui.app.plus
        assert plus is not None

        plus.add_v1_account_transaction(
            {'type': 'REMOVE_PLAYER_PROFILE', 'name': self.selected_profile}
        )

        # Go back to default selection.
        type(self).selected_profile = None

        plus.run_v1_account_transactions()
        bui.getsound('shieldDown').play()
        self._refresh()

        # Select profile list.
        bui.containerwidget(
            edit=self._root_widget, selected_child=self._scrollwidget
        )

    def _edit_profile(self) -> None:
        # pylint: disable=cyclic-import
        from bauiv1lib.profile.edit import EditProfileWindow

        # No-op if we're not in control.
        if not self.main_window_has_control():
            return

        if self.selected_profile is None:
            bui.getsound('error').play()
            bui.screenmessage(
                bui.Lstr(resource='nothingIsSelectedErrorText'), color=(1, 0, 0)
            )
            return

        self.main_window_replace(
            lambda: EditProfileWindow(self.selected_profile)
        )

    def _select(self, name: str, index: int) -> None:
        del index  # Unused.
        type(self).selected_profile = name

    def _refresh(self) -> None:
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        from efro.util import asserttype
        from bascenev1 import PlayerProfilesChangedMessage
        from bascenev1lib.actor import spazappearance

        assert bui.app.classic is not None

        plus = bui.app.plus
        assert plus is not None

        old_selection = self.selected_profile

        # Delete old.
        while self._profile_widgets:
            self._profile_widgets.pop().delete()
        self._profiles = bui.app.config.get('Player Profiles', {})
        assert self._profiles is not None
        items = list(self._profiles.items())
        items.sort(key=lambda x: asserttype(x[0], str).lower())
        spazzes = spazappearance.get_appearances()
        spazzes.sort()
        icon_textures = [
            bui.gettexture(bui.app.classic.spaz_appearances[s].icon_texture)
            for s in spazzes
        ]
        icon_tint_textures = [
            bui.gettexture(
                bui.app.classic.spaz_appearances[s].icon_mask_texture
            )
            for s in spazzes
        ]
        index = 0
        y_val = 35 * (len(self._profiles) - 1)
        account_name: str | None
        if plus.get_v1_account_state() == 'signed_in':
            account_name = plus.get_v1_account_display_string()
        else:
            account_name = None
        widget_to_select = None
        for p_name, p_info in items:
            if p_name == '__account__' and account_name is None:
                continue
            color, _highlight = bui.app.classic.get_player_profile_colors(
                p_name
            )
            scl = 1.1
            tval = (
                account_name
                if p_name == '__account__'
                else bui.app.classic.get_player_profile_icon(p_name) + p_name
            )

            try:
                char_index = spazzes.index(p_info['character'])
            except Exception:
                char_index = spazzes.index('Spaz')

            assert isinstance(tval, str)
            txtw = bui.textwidget(
                parent=self._subcontainer,
                id=f'{self.main_window_id_prefix}|profile{index}',
                position=(5, y_val),
                size=((self._width - 210) / scl, 28),
                text=bui.Lstr(value=f'    {tval}'),
                h_align='left',
                v_align='center',
                on_select_call=bui.WeakCallStrict(self._select, p_name, index),
                maxwidth=self._scroll_width * 0.86,
                corner_scale=scl,
                color=bui.safecolor(color, 0.4),
                always_highlight=True,
                on_activate_call=bui.CallStrict(self._edit_button.activate),
                selectable=True,
            )
            # We handle reselection of these manually; no need for ids.
            bui.widget(edit=txtw, allow_preserve_selection=False)

            character = bui.imagewidget(
                parent=self._subcontainer,
                position=(0, y_val),
                size=(30, 30),
                color=(1, 1, 1),
                mask_texture=bui.gettexture('characterIconMask'),
                tint_color=color,
                tint2_color=_highlight,
                texture=icon_textures[char_index],
                tint_texture=icon_tint_textures[char_index],
            )
            if index == 0:
                bui.widget(edit=txtw, up_widget=self._back_button)
                if self.selected_profile is None:
                    type(self).selected_profile = p_name
            bui.widget(edit=txtw, show_buffer_top=40, show_buffer_bottom=40)
            self._profile_widgets.append(txtw)
            self._profile_widgets.append(character)

            # Select/show this one if it was previously selected.
            # (but defer till after this loop since our height is
            # still changing).
            if p_name == old_selection or widget_to_select is None:
                widget_to_select = txtw

            index += 1
            y_val -= 35

        bui.containerwidget(
            edit=self._subcontainer,
            size=(self._scroll_width, index * 35),
        )
        if widget_to_select is not None:
            bui.containerwidget(
                edit=self._subcontainer,
                selected_child=widget_to_select,
                visible_child=widget_to_select,
            )

        # If there's a team-chooser in existence, tell it the profile-list
        # has probably changed.
        session = bs.get_foreground_host_session()
        if session is not None:
            session.handlemessage(PlayerProfilesChangedMessage())
