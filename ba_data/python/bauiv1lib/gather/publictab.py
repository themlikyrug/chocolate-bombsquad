# Released under the MIT License. See LICENSE for details.
#
# pylint: disable=too-many-lines
"""Defines the public tab in the gather UI."""

from __future__ import annotations

import copy
import time
from threading import Thread
from enum import Enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override
import weakref

from bauiv1lib.gather import GatherTab
from mell.party_queue import PartyQueueHandler
import bauiv1 as bui
import bascenev1 as bs

if TYPE_CHECKING:
    from typing import Callable, Any

    from bauiv1lib.gather import GatherWindow

# Print a bit of info about pings, queries, etc.
DEBUG_SERVER_COMMUNICATION = False
DEBUG_PROCESSING = False

PARTY_ENTRY_BUTTON_HEIGHT = 120

class PartyEntryWindow(bui.Window):
    """A window that handles a join and 
    stats button for a party entry, triggered 
    after clicking a party's button."""
    def __init__(
        self, 
        party_entry: PartyEntry,
        origin=(0, 0),
    ):
        self._party_entry = party_entry
        # Generally just want a small window
        # BUT wanna scale it up for smaller UI scales.
        width = 360
        height = 180
        stats = party_entry.stats_addr
        button_width = width * 0.88
        button_height = 68
        button_scale = 0.85
        # If we already know we have stats from the get-go,
        # increase our height. This seems somewhat stupid,
        # but makes the UI more compact for us.
        if stats:
            height += button_height
        uiscale = bui.app.ui_v1.uiscale
        scale = (
            1.8 if uiscale is bui.UIScale.SMALL
            else 1.3 if uiscale is bui.UIScale.MEDIUM
            else 1.0
        )
        super().__init__(
            root_widget=bui.containerwidget(
                size=(width, height),
                stack_offset=origin,
                scale_origin_stack_offset=origin,
                scale=scale,
                background=False,
                # FIXME: find a way to inherit this somehow...?
                toolbar_visibility=(
                    'menu_tokens' 
                    if uiscale is bui.UIScale.SMALL 
                    else 'menu_full'
                ),
                on_outside_click_call=self.close,
            )
        )
        

        extrasize = 60
        bui.imagewidget(
            parent=self._root_widget,
            texture=bui.gettexture('softRect2'),
            size=(width + extrasize, height + extrasize),
            position=(-extrasize * 0.5, -extrasize * 0.5),
            color=(0, 0, 0),
            opacity=0.8,
        )
        
        bui.containerwidget(
            edit=self._root_widget,
            transition='in_scale',
        )
        
        self._back_button = btn = bui.buttonwidget(
            parent=self._root_widget,
            position=(-5, height - 35),
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
            text=bui.Lstr(value=party_entry.name),
            position=(width * 0.5, height - 18),
            size=(0, 0),
            h_align='center',
            v_align='center',
            scale=1.35,
            maxwidth=width - 80,
            color=(1.0, 1.0, 0.95),
            shadow=0.5,
            glow_type='uniform',
        )
        
        info_spacing = 65
        plus = bui.app.plus
        assert plus is not None
        ping_good = plus.get_v1_account_misc_read_val('pingGood', 100)
        ping_med = plus.get_v1_account_misc_read_val('pingMed', 500)
        
        if party_entry.ping:
            ping_color = (
                (0.1, 1.0, 0.2)
                if party_entry.ping <= ping_good
                else (1.0, 0.95, 0.1) 
                if party_entry.ping <= ping_med 
                else (1.0, 0.2, 0.2)
            )
            ping_text = f'{int(party_entry.ping)}ms'
        else:
            ping_color = (0.5, 0.5, 0.5)
            ping_text = '-'
        
        # Label for the ping counter
        counter_y = height - 42
        bui.textwidget(
            parent=self._root_widget,
            text=bui.Lstr(resource='gatherWindow.pingText'),
            position=((width * 0.5) - info_spacing, counter_y),
            size=(0, 0),
            h_align='center',
            scale=0.65,
            color=(0.7, 0.7, 0.7),
            maxwidth=width - 70,
        )
        # Actual frickin counter
        bui.textwidget(
            parent=self._root_widget,
            text=ping_text,
            position=((width * 0.5) - info_spacing, counter_y - 14),
            size=(0, 0),
            h_align='center',
            scale=1.25,
            color=ping_color,
            shadow=0.4,
            glow_type='uniform',
            maxwidth=width - (70 + info_spacing),
        )
        
        # Label for the party size
        bui.textwidget(
            parent=self._root_widget,
            text=bui.Lstr(resource='gatherWindow.partySizeText'),
            position=((width * 0.5) + info_spacing, counter_y),
            size=(0, 0),
            h_align='center',
            scale=0.65,
            color=(0.7, 0.7, 0.7),
            maxwidth=width - 70,
        )
        # Actual frickin counter
        bui.textwidget(
            parent=self._root_widget,
            text=f'{party_entry.size}/{party_entry.size_max}',
            position=((width * 0.5) + info_spacing, counter_y - 14),
            size=(0, 0),
            h_align='center',
            scale=1.25,
            color=(0.2, 0.8, 1.0),
            shadow=0.4,
            glow_type='uniform',
            maxwidth=width - (70 + info_spacing),
        )
        textscale = 1.25
        v = -15 + (button_height * 0.5) * button_scale
        
        self._join_btn = bui.buttonwidget(
            parent=self._root_widget,
            label=bui.Lstr(resource='gatherWindow.manualConnectText'),
            position=(width * 0.5 - (button_width * 0.5) * button_scale, v),
            size=(button_width, button_height),
            scale=button_scale,
            icon=bui.gettexture('startButton'),
            text_scale=textscale,
            iconscale=textscale * 1.1,
            on_activate_call=self._join,
            autoselect=True,
            texture=bui.gettexture('softRect2'),
            color=(0.15, 0.65, 0.25),
            textcolor=(1.0, 1.0, 1.0),
        )
        
        bui.containerwidget(
            edit=self._root_widget,
            start_button=self._join_btn,
        )
        
        stats = party_entry.stats_addr
        if stats:
            plus = bui.app.plus
            assert plus is not None
            url = party_entry.stats_addr.replace(
                '${ACCOUNT}',
                plus.get_v1_account_misc_read_val_2(
                    'resolvedAccountID', 'UNKNOWN'
                ),
            )
            v += (button_height + 12) * button_scale
            self._stats_btn = bui.buttonwidget(
                parent=self._root_widget,
                label=bui.Lstr(resource='statsText'),
                position=(width * 0.5 - (button_width * 0.5) * button_scale, v),
                size=(button_width, button_height),
                scale=button_scale,
                color=(0.15, 0.35, 0.75),
                textcolor=(0.9, 0.95, 1.0),
                icon=bui.gettexture('cuteSpaz'),
                text_scale=textscale,
                iconscale=textscale * 1.1,
                on_activate_call=bui.CallPartial(bui.open_url, url),
                autoselect=True,
                texture=bui.gettexture('softRect2'),
            )

    def _join(self):
        # Let the queue handle it.
        party = self._party_entry
        data = {
            'address': party.address,
            'port': party.port,
            'name': party.name,
            'queue_id': party.queue,
            'size': (party.size, party.size_max),
        }
        if bui.app._party_queue_handler:
            bui.app._party_queue_handler._clear_actor()
        bui.app._party_queue_handler = PartyQueueHandler(data)
        # Close too.
        self.close()
    
    def close(self):
        # No-op if we're already closing.
        if (
            not self._root_widget 
            or self._root_widget.transitioning_out
        ):
            return
        bui.containerwidget(
            edit=self._root_widget,
            transition='out_scale',
        )
        


class SubTabType(Enum):
    """Available sub-tabs."""

    JOIN = 'join'
    HOST = 'host'

class SortType(Enum):
    NAME = 'name'
    PING = 'ping'
    SIZE = 'size'

class SortSubType(Enum):
    INCREASING = 'increasing'
    DECREASING = 'decreasing'
    
DEFAULT_SORT_TYPE = SortType.PING
DEFAULT_SORT_SUBTYPE = SortSubType.DECREASING


@dataclass
class PartyEntry:
    """Info about a public party."""

    address: str
    index: int
    queue: str | None = None
    port: int = -1
    name: str = ''
    size: int = -1
    size_max: int = -1
    claimed: bool = False
    ping: float | None = None
    ping_interval: float = -1.0
    next_ping_time: float = -1.0
    ping_attempts: int = 0
    ping_responses: int = 0
    stats_addr: str | None = None
    clean_display_index: int | None = None

    def get_key(self) -> str:
        """Return the key used to store this party."""
        return f'{self.address}_{self.port}'


class UIRow:
    """Wrangles UI for a row in the party list."""

    def __init__(self) -> None:
        self._name_widget: bui.Widget | None = None
        self._size_widget: bui.Widget | None = None
        self._ping_widget: bui.Widget | None = None
        self._button_widget: bui.Widget | None = None
        self._stats_widget: bui.Widget | None = None

    def __del__(self) -> None:
        self._clear()

    def _clear(self) -> None:
        for widget in [
            self._name_widget,
            self._size_widget,
            self._ping_widget,
            self._button_widget,
            self._stats_widget,
        ]:
            if widget:
                widget.delete()

    def update(
        self,
        index: int,
        party: PartyEntry,
        sub_scroll_width: float,
        sub_scroll_height: float,
        lineheight: float,
        columnwidget: bui.Widget,
        join_text: bui.Widget,
        filter_text: bui.Widget,
        existing_selection: Selection | None,
        tab: PublicGatherTab,
    ) -> None:
        """Update for the given data."""
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-positional-arguments

        plus = bui.app.plus
        assert plus is not None

        # Quick-out: if we've been marked clean for a certain index and
        # we're still at that index, we're done.
        if party.clean_display_index == index:
            return

        ping_good = plus.get_v1_account_misc_read_val('pingGood', 100)
        ping_med = plus.get_v1_account_misc_read_val('pingMed', 500)

        self._clear()
        hpos = 0
        button_width = sub_scroll_width - 5
        button_height = PARTY_ENTRY_BUTTON_HEIGHT
        button_spacing = button_height + 2
        top_of_btn = (button_height - 100)
        # i GUESS bro
        vpos = (sub_scroll_height - (button_height - 30)) - (button_spacing * index)
        main = self._button_widget = bui.buttonwidget(
            parent=columnwidget,
            position=(
                hpos, 
                vpos - (button_height * 0.5),
            ),
            size=(button_width, button_height),
            label='',
            on_select_call=bui.WeakCallStrict(
                tab.set_public_party_selection,
                Selection(party.get_key(), SelectionComponent.NAME),
            ),
            on_activate_call=bui.WeakCallStrict(
                tab.on_public_party_activate, party
            ),
        )
        name = bui.textwidget(
            parent=columnwidget,
            text=bui.Lstr(value=party.name),
            size=(0, 0),
            scale=1.2,
            position=(50 + hpos, vpos + top_of_btn),
            maxwidth=button_width * 0.8,
            autoselect=True,
            color=(1, 1, 1, 0.3 if party.ping is None else 1.0),
            h_align='left',
            v_align='center',
            draw_controller=main,
        )
        # These are popping in and out too chaotically to try and do
        # auto-select-save/restore, so we don't supply ids for them. We
        # need to suppress the warning that comes with that though.
        bui.widget(edit=main, allow_preserve_selection=False)

        bui.widget(
            edit=main,
            left_widget=join_text,
            show_buffer_top=64.0,
            show_buffer_bottom=64.0,
        )
        bui.widget(
            edit=name,
            show_buffer_top=64.0,
            show_buffer_bottom=64.0,
        )
        if existing_selection == Selection(
            party.get_key(), SelectionComponent.NAME
        ):
            bui.containerwidget(
                edit=columnwidget, 
                selected_child=main
            )

        size = bui.textwidget(
            text=str(party.size) + '/' + str(party.size_max),
            parent=columnwidget,
            size=(0, 0),
            position=(hpos + (button_width - 140), vpos + top_of_btn),
            scale=0.9,
            color=(0.8, 0.8, 0.8),
            h_align='right',
            v_align='center',
            draw_controller=main,
        )

        if index == 0:
            bui.widget(edit=name, up_widget=filter_text)

        ping = bui.textwidget(
            parent=columnwidget,
            size=(0, 0),
            position=(hpos + (button_width - 60), vpos + top_of_btn),
            scale=0.9,
            h_align='right',
            v_align='center',
            draw_controller=main,
        )
        if party.ping is None:
            bui.textwidget(
                edit=ping, text='-', color=(0.5, 0.5, 0.5)
            )
        else:
            bui.textwidget(
                edit=ping,
                text=f'{int(party.ping)}ms',
                color=(
                    (0, 1, 0)
                    if party.ping <= ping_good
                    else (1, 1, 0) if party.ping <= ping_med else (1, 0, 0)
                ),
            )
        stats = party.stats_addr
        # NOTE: We don't normally need this since
        # the stats button is in the party entry window, but
        # this makes things look less empty.
        stats_w = None
        if stats:
            url = party.stats_addr.replace(
                '${ACCOUNT}',
                plus.get_v1_account_misc_read_val_2(
                    'resolvedAccountID', 'UNKNOWN'
                ),
            )
            stats_w = bui.textwidget(
                parent=columnwidget,
                text=bui.Lstr(value=url),
                size=(0, 0),
                position=(50 + hpos, vpos + (top_of_btn - 35)),
                maxwidth=button_width * 0.8,
                autoselect=True,
                color=(0.8, 0.8, 0.8),
                h_align='left',
                v_align='center',
                draw_controller=main,
            )
        # Oh Yeah We Do Need To Save These
        self._name_widget = name
        self._ping_widget = ping
        self._size_widget = size
        self._stats_widget = stats_w
        party.clean_display_index = index


@dataclass
class State:
    """State saved/restored only while the app is running."""

    sub_tab: SubTabType = SubTabType.JOIN
    parties: list[tuple[str, PartyEntry]] | None = None
    next_entry_index: int = 0
    filter_value: str = ''
    have_server_list_response: bool = False
    have_valid_server_list: bool = False


class SelectionComponent(Enum):
    """Describes what part of an entry is selected."""

    NAME = 'name'
    STATS_BUTTON = 'stats_button'


@dataclass
class Selection:
    """Describes the currently selected list element."""

    entry_key: str
    component: SelectionComponent


class AddrFetchThread(Thread):
    """Thread for fetching an address in the bg."""

    def __init__(self, call: Callable[[Any], Any]):
        super().__init__()
        self._call = call

    @override
    def run(self) -> None:
        sock: socket.socket | None = None
        try:
            # FIXME: Update this to work with IPv6 at some point.
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(('8.8.8.8', 80))
            val = sock.getsockname()[0]
            bui.pushcall(
                bui.CallStrict(self._call, val), from_other_thread=True
            )
        except Exception as exc:
            from efro.error import is_udp_communication_error

            # Ignore expected network errors; log others.
            if is_udp_communication_error(exc):
                pass
            else:
                bui.netlog.exception('Error in addr-fetch-thread')
        finally:
            if sock is not None:
                sock.close()


class PingThread(Thread):
    """Thread for sending out game pings."""

    def __init__(
        self,
        address: str,
        port: int,
        call: Callable[[str, int, float | None], int | None],
    ):
        super().__init__()
        self._address = address
        self._port = port
        self._call = call

    @override
    def run(self) -> None:
        assert bui.app.classic is not None
        bui.app.classic.ping_thread_count += 1
        sock: socket.socket | None = None

        # Prevent shutdown while our thread is doing its thing.
        if not bui.shutdown_suppress_begin():
            # App is already shutting down, so we're a no-op.
            return

        try:
            import socket

            socket_type = bui.get_ip_address_type(self._address)
            sock = socket.socket(socket_type, socket.SOCK_DGRAM)
            sock.connect((self._address, self._port))

            accessible = False
            starttime = time.time()

            # Send a few pings and wait a second for a response.
            sock.settimeout(1)
            for _i in range(3):
                sock.send(b'\x0b')
                result: bytes | None
                try:
                    # 11: BA_PACKET_SIMPLE_PING
                    result = sock.recv(10)
                except Exception:
                    result = None
                if result == b'\x0c':
                    # 12: BA_PACKET_SIMPLE_PONG
                    accessible = True
                    break
                time.sleep(1)
            ping = (time.time() - starttime) * 1000.0
            bui.pushcall(
                bui.CallStrict(
                    self._call,
                    self._address,
                    self._port,
                    ping if accessible else None,
                ),
                from_other_thread=True,
            )
        except Exception as exc:
            from efro.error import is_udp_communication_error

            if is_udp_communication_error(exc):
                pass
            else:
                if bui.do_once():
                    bui.netlog.exception('Error on gather ping.')
        finally:
            try:
                if sock is not None:
                    sock.close()
            except Exception:
                if bui.do_once():
                    bui.netlog.exception('Error on gather ping cleanup')

        bui.app.classic.ping_thread_count -= 1
        bui.shutdown_suppress_end()


class PublicGatherTab(GatherTab):
    """The public tab in the gather UI"""

    def __init__(self, window: GatherWindow) -> None:
        super().__init__(window)
        self._idprefix = f'{window.main_window_id_prefix}|public'
        self._container: bui.Widget | None = None
        self._join_text: bui.Widget | None = None
        self._host_text: bui.Widget | None = None
        self._filter_text: bui.Widget | None = None
        self._local_address: str | None = None
        self._last_connect_attempt_time: float | None = None
        self._sub_tab: SubTabType = SubTabType.JOIN
        self._selection: Selection | None = None
        self._refreshing_list = False
        self._update_timer: bui.AppTimer | None = None
        self._host_scrollwidget: bui.Widget | None = None
        self._host_name_text: bui.Widget | None = None
        self._host_toggle_button: bui.Widget | None = None
        self._last_server_list_query_time: float | None = None
        self._join_list_column: bui.Widget | None = None
        self._join_status_text: bui.Widget | None = None
        self._join_status_spinner: bui.Widget | None = None
        self._no_servers_found_text: bui.Widget | None = None
        self._host_max_party_size_value: bui.Widget | None = None
        self._host_max_party_size_minus_button: bui.Widget | None = None
        self._host_max_party_size_plus_button: bui.Widget | None = None
        self._join_sub_scroll_width: float | None = None
        self._host_status_text: bui.Widget | None = None
        self._signed_in = False
        self._ui_rows: list[UIRow] = []
        self._ui_rows_by_party: dict[int, UIRow] = {}
        self._refresh_ui_row = 0
        self._have_user_selected_row = False
        self._first_valid_server_list_time: float | None = None
        
        inc = SortSubType.INCREASING
        dec = SortSubType.DECREASING
        self._sort_subtype = DEFAULT_SORT_SUBTYPE
        self._sort_type = None
        self._last_sort_type = self._sort_type
        self._sort_widget_names = {}

        # Parties indexed by id:
        self._parties: dict[str, PartyEntry] = {}

        # Parties sorted in display order:
        self._parties_sorted: list[tuple[str, PartyEntry]] = []
        self._party_lists_dirty = True

        # Sorted parties with filter applied:
        self._parties_displayed: dict[str, PartyEntry] = {}

        self._next_entry_index = 0
        self._have_server_list_response = False
        self._have_valid_server_list = False
        self._filter_value = ''
        self._pending_party_infos: list[dict[str, Any]] = []
        self._last_sub_scroll_height = 0.0

    @override
    def on_activate(
        self,
        parent_widget: bui.Widget,
        tab_button: bui.Widget,
        region_width: float,
        region_height: float,
        region_left: float,
        region_bottom: float,
    ) -> bui.Widget:
        # pylint: disable=too-many-positional-arguments
        c_width = region_width
        c_height = region_height - 20
        self._container = bui.containerwidget(
            parent=parent_widget,
            position=(
                region_left,
                region_bottom + (region_height - c_height) * 0.5,
            ),
            size=(c_width, c_height),
            background=False,
            selection_loops_to_parent=True,
        )
        v = c_height - 30
        self._join_text = bui.textwidget(
            parent=self._container,
            id=f'{self._idprefix}|jointab',
            position=(c_width * 0.5 - 245, v - 13),
            color=(0.6, 1.0, 0.6),
            scale=1.3,
            size=(200, 30),
            maxwidth=250,
            h_align='left',
            v_align='center',
            click_activate=True,
            selectable=True,
            autoselect=True,
            on_activate_call=lambda: self._set_sub_tab(
                SubTabType.JOIN,
                region_width,
                region_height,
                playsound=True,
            ),
            text=bui.Lstr(
                resource='gatherWindow.' 'joinPublicPartyDescriptionText'
            ),
            glow_type='uniform',
        )
        self._host_text = bui.textwidget(
            parent=self._container,
            id=f'{self._idprefix}|hosttab',
            position=(c_width * 0.5 + 45, v - 13),
            color=(0.6, 1.0, 0.6),
            scale=1.3,
            size=(200, 30),
            maxwidth=250,
            h_align='left',
            v_align='center',
            click_activate=True,
            selectable=True,
            autoselect=True,
            on_activate_call=lambda: self._set_sub_tab(
                SubTabType.HOST,
                region_width,
                region_height,
                playsound=True,
            ),
            text=bui.Lstr(
                resource='gatherWindow.' 'hostPublicPartyDescriptionText'
            ),
            glow_type='uniform',
        )
        bui.widget(edit=self._join_text, up_widget=tab_button)
        bui.widget(
            edit=self._host_text,
            left_widget=self._join_text,
            up_widget=tab_button,
        )
        bui.widget(edit=self._join_text, right_widget=self._host_text)

        # Attempt to fetch our local address so we have it for error
        # messages.
        if self._local_address is None:
            AddrFetchThread(
                bui.WeakCallPartial(self._fetch_local_addr_cb)
            ).start()

        self._set_sub_tab(self._sub_tab, region_width, region_height)
        self._update_timer = bui.AppTimer(
            0.1, bui.WeakCallStrict(self._update), repeat=True
        )
        return self._container

    @override
    def on_deactivate(self) -> None:
        self._update_timer = None

    @override
    def save_state(self) -> None:
        # Save off a small number of parties with the lowest ping; we'll
        # display these immediately when our UI comes back up which
        # should be enough to make things feel nice and crisp while we
        # do a full server re-query or whatnot.
        assert bui.app.classic is not None
        bui.app.ui_v1.window_states[type(self)] = State(
            sub_tab=self._sub_tab,
            parties=[(i, copy.copy(p)) for i, p in self._parties_sorted[:40]],
            next_entry_index=self._next_entry_index,
            filter_value=self._filter_value,
            have_server_list_response=self._have_server_list_response,
            have_valid_server_list=self._have_valid_server_list,
        )

    @override
    def restore_state(self) -> None:
        assert bui.app.classic is not None
        state = bui.app.ui_v1.window_states.get(type(self))
        if state is None:
            state = State()
        assert isinstance(state, State)
        self._sub_tab = state.sub_tab

        # Restore the parties we stored.
        if state.parties:
            self._parties = {
                key: copy.copy(party) for key, party in state.parties
            }
            self._parties_sorted = list(self._parties.items())
            self._party_lists_dirty = True

            self._next_entry_index = state.next_entry_index

            # FIXME: should save/restore these too?
            self._have_server_list_response = state.have_server_list_response
            self._have_valid_server_list = state.have_valid_server_list
        self._filter_value = state.filter_value

    def _set_sub_tab(
        self,
        value: SubTabType,
        region_width: float,
        region_height: float,
        playsound: bool = False,
    ) -> None:
        assert self._container
        if playsound:
            bui.getsound('click01').play()
        self._sort_widget_names.clear()

        # Reset our selection (prevents selecting something way down the
        # list if we switched away and came back).
        self._selection = None
        self._have_user_selected_row = False

        # Reset refresh to the top and make sure everything refreshes.
        self._refresh_ui_row = 0
        for party in self._parties.values():
            party.clean_display_index = None

        self._sub_tab = value
        active_color = (0.6, 1.0, 0.6)
        inactive_color = (0.5, 0.4, 0.5)
        bui.textwidget(
            edit=self._join_text,
            color=active_color if value is SubTabType.JOIN else inactive_color,
        )
        bui.textwidget(
            edit=self._host_text,
            color=active_color if value is SubTabType.HOST else inactive_color,
        )

        # Clear anything existing in the old sub-tab.
        for widget in self._container.get_children():
            if widget and widget not in {self._host_text, self._join_text}:
                widget.delete()

        if value is SubTabType.JOIN:
            self._build_join_tab(region_width, region_height)

        if value is SubTabType.HOST:
            self._build_host_tab(region_width, region_height)

    def _build_join_tab(
        self, region_width: float, region_height: float
    ) -> None:
        c_width = region_width
        c_height = region_height - 20
        sub_scroll_height = c_height - 125
        self._join_sub_scroll_width = sub_scroll_width = min(
            1200, region_width - 80
        )
        v = c_height - 35
        v -= 60
        filter_txt = bui.Lstr(resource='filterText')
        self._filter_text = bui.textwidget(
            parent=self._container,
            id=f'{self._idprefix}|filter',
            text=self._filter_value,
            size=(350, 45),
            position=(c_width * 0.5 - 150, v - 10),
            h_align='left',
            v_align='center',
            editable=True,
            maxwidth=310,
            description=filter_txt,
        )
        bui.widget(edit=self._filter_text, up_widget=self._join_text)
        bui.textwidget(
            text=filter_txt,
            parent=self._container,
            size=(0, 0),
            position=(c_width * 0.5 - 170, v + 13),
            maxwidth=150,
            scale=0.8,
            color=(0.5, 0.46, 0.5),
            flatness=1.0,
            h_align='right',
            v_align='center',
        )
        set_sorting = self.set_sorting
        text_width_scale = 25
        text_widget_scale = 0.8
        height = 34

        text = bui.Lstr(resource='nameText')
        eval = text.evaluate()
        width = len(eval) * text_width_scale
        type = SortType.NAME
        widget = bui.textwidget(
            text=text,
            parent=self._container,
            size=(width, height),
            position=(
                ((c_width - sub_scroll_width) * 0.5 + 50) - (width * 0.5), 
                v - 8 - (height * 0.5),
            ),
            maxwidth=60,
            scale=text_widget_scale,
            color=(0.5, 0.46, 0.5),
            flatness=1.0,
            h_align='center',
            v_align='center',
            selectable=True,
            click_activate=True,
        )
        self._sort_widget_names[widget] = text
        bui.textwidget(
            edit=widget,
            on_activate_call=bui.WeakCallPartial(
               set_sorting,
               widget=widget,
               type=type,
            ),
        )
        
        text = bui.Lstr(resource='gatherWindow.partySizeText')
        eval = text.evaluate()
        width = len(eval) * text_width_scale
        type = SortType.SIZE
        widget = bui.textwidget(
            text=text,
            parent=self._container,
            size=(width, height),
            position=(
                (c_width * 0.5 + sub_scroll_width * 0.5 - 140) - (width * 0.5),
                v - 8 - (height * 0.5),
            ),
            maxwidth=60,
            scale=text_widget_scale,
            color=(0.5, 0.46, 0.5),
            flatness=1.0,
            h_align='center',
            v_align='center',
            selectable=True,
            click_activate=True,
        )
        self._sort_widget_names[widget] = text
        bui.textwidget(
            edit=widget,
            on_activate_call=bui.WeakCallPartial(
               set_sorting,
               widget=widget,
               type=type,
            ),
        )
        
        text = bui.Lstr(resource='gatherWindow.pingText')
        eval = text.evaluate()
        width = len(eval) * text_width_scale
        type = SortType.PING
        widget = bui.textwidget(
            text=text,
            parent=self._container,
            size=(width, height),
            position=(
                (c_width * 0.5 + sub_scroll_width * 0.5 - 50) - (width * 0.5),
                v - 8 - (height * 0.5),
            ),
            maxwidth=60,
            scale=text_widget_scale,
            color=(0.5, 0.46, 0.5),
            flatness=1.0,
            h_align='center',
            v_align='center',
            selectable=True,
            click_activate=True,
        )
        self._sort_widget_names[widget] = text
        bui.textwidget(
            edit=widget,
            on_activate_call=bui.WeakCallPartial(
               set_sorting,
               widget=widget,
               type=type,
            ),
        )
        # trol
        bui.WeakCallPartial(
           set_sorting,
           widget=widget,
           type=type,
        )()
        
        v -= sub_scroll_height + 23
        self._host_scrollwidget = scrollw = bui.scrollwidget(
            parent=self._container,
            simple_culling_v=10,
            position=((c_width - sub_scroll_width) * 0.5, v),
            size=(sub_scroll_width, sub_scroll_height),
            claims_up_down=False,
            claims_left_right=True,
            autoselect=True,
        )
        self._join_list_column = bui.containerwidget(
            parent=scrollw,
            id=f'{self._idprefix}|joinlistcolumn',
            background=False,
            size=(400, 400),
            claims_left_right=True,
        )

        # Create join status text and join spinner. Always make sure to
        # update both of these together.
        self._join_status_text = bui.textwidget(
            parent=self._container,
            text='',
            size=(0, 0),
            scale=0.9,
            flatness=1.0,
            shadow=0.0,
            h_align='center',
            v_align='top',
            maxwidth=c_width,
            color=(0.6, 0.6, 0.6),
            position=(c_width * 0.5, c_height * 0.5),
        )
        self._join_status_spinner = bui.spinnerwidget(
            parent=self._container,
            position=(c_width * 0.5, c_height * 0.5),
            style='bomb',
            size=64,
        )

        self._no_servers_found_text = bui.textwidget(
            parent=self._container,
            text='',
            size=(0, 0),
            scale=0.9,
            flatness=1.0,
            shadow=0.0,
            h_align='center',
            v_align='top',
            color=(0.6, 0.6, 0.6),
            position=(c_width * 0.5, c_height * 0.5),
        )

    def _build_host_tab(
        self, region_width: float, region_height: float
    ) -> None:
        c_width = region_width
        c_height = region_height - 20
        v = c_height - 35
        v -= 25
        is_public_enabled = bs.get_public_party_enabled()
        v -= 30

        bui.textwidget(
            parent=self._container,
            size=(0, 0),
            h_align='center',
            v_align='center',
            maxwidth=c_width * 0.9,
            scale=0.7,
            flatness=1.0,
            color=(0.5, 0.46, 0.5),
            position=(region_width * 0.5, v + 10),
            text=bui.Lstr(resource='gatherWindow.publicHostRouterConfigText'),
        )
        v -= 30

        # Nudge party name and size values to be mostly centered.
        xoffs = region_width * 0.5 - 500

        party_name_text = bui.Lstr(
            resource='gatherWindow.partyNameText',
            fallback_resource='editGameListWindow.nameText',
        )
        assert bui.app.classic is not None
        bui.textwidget(
            parent=self._container,
            size=(0, 0),
            h_align='right',
            v_align='center',
            maxwidth=200,
            scale=0.8,
            color=bui.app.ui_v1.infotextcolor,
            position=(210 + xoffs, v - 9),
            text=party_name_text,
        )
        self._host_name_text = bui.textwidget(
            parent=self._container,
            id=f'{self._idprefix}|hostingname',
            editable=True,
            size=(535, 40),
            position=(230 + xoffs, v - 30),
            text=bui.app.config.get('Public Party Name', ''),
            maxwidth=494,
            shadow=0.3,
            flatness=1.0,
            description=party_name_text,
            autoselect=True,
            v_align='center',
            corner_scale=1.0,
        )

        v -= 60
        bui.textwidget(
            parent=self._container,
            size=(0, 0),
            h_align='right',
            v_align='center',
            maxwidth=200,
            scale=0.8,
            color=bui.app.ui_v1.infotextcolor,
            position=(210 + xoffs, v - 9),
            text=bui.Lstr(
                resource='maxPartySizeText',
                fallback_resource='maxConnectionsText',
            ),
        )
        self._host_max_party_size_value = bui.textwidget(
            parent=self._container,
            size=(0, 0),
            h_align='center',
            v_align='center',
            scale=1.2,
            color=(1, 1, 1),
            position=(240 + xoffs, v - 9),
            text=str(bs.get_public_party_max_size()),
        )
        btn1 = self._host_max_party_size_minus_button = bui.buttonwidget(
            parent=self._container,
            id=f'{self._idprefix}|maxsizeminus',
            size=(40, 40),
            on_activate_call=bui.WeakCallStrict(
                self._on_max_public_party_size_minus_press
            ),
            position=(280 + xoffs, v - 26),
            label='-',
            autoselect=True,
        )
        btn2 = self._host_max_party_size_plus_button = bui.buttonwidget(
            parent=self._container,
            id=f'{self._idprefix}|maxsizeplus',
            size=(40, 40),
            on_activate_call=bui.WeakCallStrict(
                self._on_max_public_party_size_plus_press
            ),
            position=(350 + xoffs, v - 26),
            label='+',
            autoselect=True,
        )
        v -= 50
        v -= 70
        if is_public_enabled:
            label = bui.Lstr(
                resource='gatherWindow.makePartyPrivateText',
                fallback_resource='gatherWindow.stopAdvertisingText',
            )
        else:
            label = bui.Lstr(
                resource='gatherWindow.makePartyPublicText',
                fallback_resource='gatherWindow.startAdvertisingText',
            )
        self._host_toggle_button = bui.buttonwidget(
            parent=self._container,
            id=f'{self._idprefix}|hosttoggle',
            label=label,
            size=(400, 80),
            on_activate_call=(
                self._on_stop_advertising_press
                if is_public_enabled
                else self._on_start_advertizing_press
            ),
            position=(c_width * 0.5 - 200, v),
            autoselect=True,
            up_widget=btn2,
        )
        bui.widget(edit=self._host_name_text, down_widget=btn2)
        bui.widget(edit=btn2, up_widget=self._host_name_text)
        bui.widget(edit=btn1, up_widget=self._host_name_text)
        assert self._join_text is not None
        bui.widget(edit=self._join_text, down_widget=self._host_name_text)
        v -= 10
        self._host_status_text = bui.textwidget(
            parent=self._container,
            text=bui.Lstr(resource='gatherWindow.' 'partyStatusNotPublicText'),
            size=(0, 0),
            scale=0.7,
            flatness=1.0,
            h_align='center',
            v_align='top',
            maxwidth=c_width * 0.9,
            color=(0.6, 0.56, 0.6),
            position=(c_width * 0.5, v),
        )
        v -= 90
        bui.textwidget(
            parent=self._container,
            text=bui.Lstr(resource='gatherWindow.dedicatedServerInfoText'),
            size=(0, 0),
            scale=0.7,
            flatness=1.0,
            h_align='center',
            v_align='center',
            maxwidth=c_width * 0.9,
            color=(0.5, 0.46, 0.5),
            position=(c_width * 0.5, v),
        )

        # If public sharing is already on, launch a status-check
        # immediately.
        if bs.get_public_party_enabled():
            self._do_status_check()

    def _on_public_party_query_result(
        self, result: dict[str, Any] | None
    ) -> None:
        starttime = time.time()
        self._have_server_list_response = True

        if result is None:
            self._have_valid_server_list = False
            return

        if not self._have_valid_server_list:
            self._first_valid_server_list_time = time.time()

        self._have_valid_server_list = True
        parties_in = result['l']

        assert isinstance(parties_in, list)
        self._pending_party_infos += parties_in

        # To avoid causing a stutter here, we do most processing of
        # these entries incrementally in our _update() method. The one
        # thing we do here is prune parties not contained in this
        # result.
        for partyval in list(self._parties.values()):
            partyval.claimed = False
        for party_in in parties_in:
            addr = party_in['a']
            assert isinstance(addr, str)
            port = party_in['p']
            assert isinstance(port, int)
            party_key = f'{addr}_{port}'
            party = self._parties.get(party_key)
            if party is not None:
                party.claimed = True
        self._parties = {
            key: val for key, val in list(self._parties.items()) if val.claimed
        }
        self._parties_sorted = [p for p in self._parties_sorted if p[1].claimed]
        self._party_lists_dirty = True

        if DEBUG_PROCESSING:
            print(
                f'Handled public party query results in '
                f'{time.time()-starttime:.5f}s.'
            )

    def _update(self) -> None:
        """Periodic updating."""

        plus = bui.app.plus
        assert plus is not None

        if self._sub_tab is SubTabType.JOIN:
            # Keep our filter-text up to date from the UI.
            text = self._filter_text
            if text:
                filter_value = cast(str, bui.textwidget(query=text))
                if filter_value != self._filter_value:
                    self._filter_value = filter_value
                    self._party_lists_dirty = True

                    # Also wipe out party clean-row states (otherwise if
                    # a party disappears from a row due to filtering and
                    # then reappears on that same row when the filter is
                    # removed it may not update).
                    for party in self._parties.values():
                        party.clean_display_index = None

            self._query_party_list_periodically()
            self._ping_parties_periodically()

        # If any new party infos have come in, apply some of them.
        self._process_pending_party_infos()

        # Anytime we sign in/out, make sure we refresh our list.
        signed_in = plus.get_v1_account_state() == 'signed_in'
        if self._signed_in != signed_in:
            self._signed_in = signed_in
            self._party_lists_dirty = True

        # Update sorting to account for ping updates, new parties, etc.
        self._update_party_lists()

        # If we've got a party-name text widget, keep its value plugged
        # into our public host name.
        text = self._host_name_text
        if text:
            name = cast(str, bui.textwidget(query=self._host_name_text))
            bs.set_public_party_name(name)

        # Update status text and loading spinner.
        if self._join_status_text:
            assert self._join_status_spinner
            if not signed_in:
                bui.textwidget(
                    edit=self._join_status_text,
                    text=bui.Lstr(resource='notSignedInText'),
                )
                bui.spinnerwidget(edit=self._join_status_spinner, visible=False)
            else:
                # If we have a valid list, show no status; just the
                # list. Otherwise show either 'loading...' or 'error'
                # depending on whether this is our first go-round.
                if self._have_valid_server_list:
                    bui.textwidget(edit=self._join_status_text, text='')
                    bui.spinnerwidget(
                        edit=self._join_status_spinner, visible=False
                    )
                else:
                    if self._have_server_list_response:
                        bui.textwidget(
                            edit=self._join_status_text,
                            text=bui.Lstr(resource='errorText'),
                        )
                        bui.spinnerwidget(
                            edit=self._join_status_spinner, visible=False
                        )
                    else:
                        # Show our loading spinner.
                        bui.textwidget(edit=self._join_status_text, text='')
                        bui.spinnerwidget(
                            edit=self._join_status_spinner, visible=True
                        )

        self._update_party_rows()

    def _update_party_rows(self) -> None:
        plus = bui.app.plus
        assert plus is not None

        columnwidget = self._join_list_column
        if not columnwidget:
            return

        assert self._join_text
        assert self._filter_text

        # Janky - allow escaping when there's nothing in our list.
        assert self._host_scrollwidget
        bui.containerwidget(
            edit=self._host_scrollwidget,
            claims_up_down=(len(self._parties_displayed) > 0),
        )
        bui.textwidget(edit=self._no_servers_found_text, text='')

        # Clip if we have more UI rows than parties to show.
        clipcount = len(self._ui_rows) - len(self._parties_displayed)
        if clipcount > 0:
            clipcount = max(clipcount, 50)
            self._ui_rows = self._ui_rows[:-clipcount]

        # If we have no parties to show, we're done.
        if self._have_valid_server_list and not self._parties_displayed:
            bui.textwidget(
                edit=self._no_servers_found_text,
                text=bui.Lstr(resource='noServersFoundText'),
            )
            return

        assert self._join_sub_scroll_width is not None
        sub_scroll_width = self._join_sub_scroll_width
        lineheight = PARTY_ENTRY_BUTTON_HEIGHT
        sub_scroll_height = lineheight * (len(self._parties_displayed) + 1)
        bui.containerwidget(
            edit=columnwidget, size=(sub_scroll_width, sub_scroll_height)
        )

        # Any time our height changes, reset the refresh back to the top
        # so we don't see ugly empty spaces appearing during initial
        # list filling.
        if sub_scroll_height != self._last_sub_scroll_height:
            self._refresh_ui_row = 0
            self._last_sub_scroll_height = sub_scroll_height

            # Also note that we need to redisplay everything since its
            # pos will have changed.. :(
            for party in self._parties.values():
                party.clean_display_index = None

        # Ew; this rebuilding generates deferred selection callbacks so
        # we need to push deferred notices so we know to ignore them.
        def refresh_on() -> None:
            self._refreshing_list = True

        bui.pushcall(refresh_on)

        # Ok, now here's the deal: we want to avoid creating/updating
        # this entire list at one time because it will lead to hitches.
        # So we refresh individual rows quickly in a loop.
        rowcount = min(12, len(self._parties_displayed))

        party_vals_displayed = list(self._parties_displayed.values())
        while rowcount > 0:
            refresh_row = self._refresh_ui_row % len(self._parties_displayed)
            if refresh_row >= len(self._ui_rows):
                self._ui_rows.append(UIRow())
                refresh_row = len(self._ui_rows) - 1
            party = party_vals_displayed[refresh_row]
            uirow = self._ui_rows[refresh_row]
            # Okay. Whatever.
            self._ui_rows_by_party[id(party)] = weakref.ref(uirow)

            # For the first few seconds after getting our first
            # server-list, refresh only the top section of the list;
            # this allows the lowest ping servers to show up more
            # quickly.
            if self._first_valid_server_list_time is not None:
                if time.time() - self._first_valid_server_list_time < 4.0:
                    if refresh_row > 40:
                        refresh_row = 0
            # Might aswell change this.
            uirow.update(
                refresh_row,
                party,
                sub_scroll_width=sub_scroll_width,
                sub_scroll_height=sub_scroll_height,
                lineheight=lineheight,
                columnwidget=columnwidget,
                join_text=self._join_text,
                existing_selection=self._selection,
                filter_text=self._filter_text,
                tab=self,
            )
            self._refresh_ui_row = refresh_row + 1
            rowcount -= 1

        # So our selection callbacks can start firing..
        def refresh_off() -> None:
            self._refreshing_list = False

        bui.pushcall(refresh_off)

    def _process_pending_party_infos(self) -> None:
        starttime = time.time()

        # We want to do this in small enough pieces to not cause UI
        # hitches.
        chunksize = 30
        parties_in = self._pending_party_infos[:chunksize]
        self._pending_party_infos = self._pending_party_infos[chunksize:]
        for party_in in parties_in:
            addr = party_in['a']
            assert isinstance(addr, str)
            port = party_in['p']
            assert isinstance(port, int)
            party_key = f'{addr}_{port}'
            party = self._parties.get(party_key)
            if party is None:
                # If this party is new to us, init it.
                party = PartyEntry(
                    address=addr,
                    next_ping_time=bui.apptime() + 0.001 * party_in['pd'],
                    index=self._next_entry_index,
                )
                self._parties[party_key] = party
                self._parties_sorted.append((party_key, party))
                self._party_lists_dirty = True
                self._next_entry_index += 1
                assert isinstance(party.address, str)
                assert isinstance(party.next_ping_time, float)

            # Now, new or not, update its values.
            party.queue = party_in.get('q')
            assert isinstance(party.queue, (str, type(None)))
            party.port = port
            party.name = party_in['n']
            assert isinstance(party.name, str)
            party.size = party_in['s']
            assert isinstance(party.size, int)
            party.size_max = party_in['sm']
            assert isinstance(party.size_max, int)

            # Server provides this in milliseconds; we use seconds.
            party.ping_interval = 0.001 * party_in['pi']
            assert isinstance(party.ping_interval, float)
            party.stats_addr = party_in['sa']
            assert isinstance(party.stats_addr, (str, type(None)))

            # Make sure the party's UI gets updated.
            party.clean_display_index = None

        if DEBUG_PROCESSING and parties_in:
            print(
                f'Processed {len(parties_in)} raw party infos in'
                f' {time.time()-starttime:.5f}s.'
            )
        
    def set_sorting(self, type: SortType, widget: bui.Widget):
        inc = SortSubType.INCREASING
        dec = SortSubType.DECREASING
        if type is self._last_sort_type:
            # FIXME: Should order this instead of a switchcase.
            self._sort_subtype = inc if self._sort_subtype is not inc else dec
        else:
            self._sort_subtype = inc
        subtype = self._sort_subtype
        self._last_sort_type = type
        self._sort_type = type
        self._update()
        # Display stuff here
        # FIXME: clean this up
        for other_widget in self._sort_widget_names.keys():
            name = self._sort_widget_names[other_widget]
            bui.textwidget(
                edit=other_widget,
                text=name,
            )
        name = self._sort_widget_names[widget]
        prefix = (
            bui.charstr(bui.SpecialChar.DOWN_ARROW)
            if subtype is dec else
            bui.charstr(bui.SpecialChar.UP_ARROW)
            if subtype is inc else 'kys'
        )
        lstr = bui.Lstr(
            value='${B}${A}${B}',
            subs=[
                ('${B}', prefix),
                ('${A}', name),
            ]
        )
        bui.textwidget(
            edit=widget,
            text=lstr,
        )
        

    def _update_party_lists(self) -> None:
        plus = bui.app.plus
        assert plus is not None

        if not self._party_lists_dirty:
            return
        starttime = time.time()
        assert len(self._parties_sorted) == len(self._parties)
        inc = SortSubType.INCREASING
        dec = SortSubType.DECREASING
        sub = self._sort_subtype
        # FIXME: Switchcase.
        if self._sort_type is SortType.PING:
            key = lambda p: (
                p[1].ping if p[1].ping is not None else 999999,
                p[1].index,
            )
        elif self._sort_type is SortType.SIZE:
            key = lambda p: (
                p[1].size,
                p[1].index,
            )
        elif self._sort_type is SortType.NAME:
            key = lambda p: (
                p[1].name,
                p[1].index,
            )
        self._parties_sorted.sort(
            key=key,
            reverse=sub is dec,
        )

        # If signed out or errored, show no parties.
        if (
            plus.get_v1_account_state() != 'signed_in'
            or not self._have_valid_server_list
        ):
            self._parties_displayed = {}
        else:
            if self._filter_value:
                filterval = self._filter_value.lower()
                self._parties_displayed = {
                    k: v
                    for k, v in self._parties_sorted
                    if filterval in v.name.lower()
                }
            else:
                self._parties_displayed = dict(self._parties_sorted)

        # Any time our selection disappears from the displayed list, go
        # back to auto-selecting the top entry.
        if (
            self._selection is not None
            and self._selection.entry_key not in self._parties_displayed
        ):
            self._have_user_selected_row = False

        # Whenever the user hasn't selected something, keep the first
        # visible row selected.
        if not self._have_user_selected_row and self._parties_displayed:
            firstpartykey = next(iter(self._parties_displayed))
            self._selection = Selection(firstpartykey, SelectionComponent.NAME)

        self._party_lists_dirty = False
        if DEBUG_PROCESSING:
            print(
                f'Sorted {len(self._parties_sorted)} parties in'
                f' {time.time()-starttime:.5f}s.'
            )

    def _query_party_list_periodically(self) -> None:
        now = bui.apptime()

        plus = bui.app.plus
        assert plus is not None

        # Fire off a new public-party query periodically.
        if (
            self._last_server_list_query_time is None
            or now - self._last_server_list_query_time
            > 0.001
            * plus.get_v1_account_misc_read_val('pubPartyRefreshMS', 10000)
        ):
            self._last_server_list_query_time = now
            if DEBUG_SERVER_COMMUNICATION:
                print('REQUESTING SERVER LIST')
            if plus.get_v1_account_state() == 'signed_in':
                plus.add_v1_account_transaction(
                    {
                        'type': 'PUBLIC_PARTY_QUERY',
                        'proto': bs.protocol_version(),
                        'lang': bui.app.lang.language,
                    },
                    callback=bui.WeakCallPartial(
                        self._on_public_party_query_result
                    ),
                )
                plus.run_v1_account_transactions()
            else:
                self._on_public_party_query_result(None)

    def _ping_parties_periodically(self) -> None:
        assert bui.app.classic is not None
        now = bui.apptime()

        # Go through our existing public party entries firing off pings
        # for any that have timed out.
        for party in list(self._parties.values()):
            if (
                party.next_ping_time <= now
                and bui.app.classic.ping_thread_count < 15
            ):
                # Crank the interval up for high-latency or
                # non-responding parties to save us some useless work.
                mult = 1
                if party.ping_responses == 0:
                    if party.ping_attempts > 4:
                        mult = 10
                    elif party.ping_attempts > 2:
                        mult = 5
                if party.ping is not None:
                    mult = (
                        10 if party.ping > 300 else 5 if party.ping > 150 else 2
                    )

                interval = party.ping_interval * mult
                if DEBUG_SERVER_COMMUNICATION:
                    print(
                        f'pinging #{party.index} cur={party.ping} '
                        f'interval={interval} '
                        f'({party.ping_responses}/{party.ping_attempts})'
                    )

                party.next_ping_time = now + party.ping_interval * mult
                party.ping_attempts += 1

                PingThread(
                    party.address,
                    party.port,
                    bui.WeakCallPartial(self._ping_callback),
                ).start()

    def _ping_callback(
        self, address: str, port: int | None, result: float | None
    ) -> None:
        # Look for a widget corresponding to this target. If we find
        # one, update our list.
        party_key = f'{address}_{port}'
        party = self._parties.get(party_key)

        if party is not None:
            # print(f'PING {party.name} {result=} {time.monotonic():.1f}')
            if result is not None:
                party.ping_responses += 1

            # We now smooth ping a bit to reduce jumping around in the
            # list (only where pings are relatively good).
            current_ping = party.ping
            if current_ping is not None and result is not None and result < 150:
                smoothing = 0.7
                party.ping = (
                    smoothing * current_ping + (1.0 - smoothing) * result
                )
            else:
                party.ping = result

            # Need to re-sort the list and update the row display.
            party.clean_display_index = None
            self._party_lists_dirty = True

    def _fetch_local_addr_cb(self, val: str) -> None:
        self._local_address = str(val)

    def _on_public_party_accessible_response(
        self, data: dict[str, Any] | None
    ) -> None:
        # If we've got status text widgets, update them.
        text = self._host_status_text
        if text:
            if data is None:
                bui.textwidget(
                    edit=text,
                    text=bui.Lstr(
                        resource='gatherWindow.' 'partyStatusNoConnectionText'
                    ),
                    color=(1, 0, 0),
                )
            else:
                if not data.get('accessible', False):
                    ex_line: str | bui.Lstr
                    if self._local_address is not None:
                        ex_line = bui.Lstr(
                            value='\n${A} ${B}',
                            subs=[
                                (
                                    '${A}',
                                    bui.Lstr(
                                        resource='gatherWindow.'
                                        'manualYourLocalAddressText'
                                    ),
                                ),
                                ('${B}', self._local_address),
                            ],
                        )
                    else:
                        ex_line = ''
                    bui.textwidget(
                        edit=text,
                        text=bui.Lstr(
                            value='${A}\n${B}${C}',
                            subs=[
                                (
                                    '${A}',
                                    bui.Lstr(
                                        resource='gatherWindow.'
                                        'partyStatusNotJoinableText'
                                    ),
                                ),
                                (
                                    '${B}',
                                    bui.Lstr(
                                        resource='gatherWindow.'
                                        'manualRouterForwardingText',
                                        subs=[
                                            (
                                                '${PORT}',
                                                str(bs.get_game_port()),
                                            )
                                        ],
                                    ),
                                ),
                                ('${C}', ex_line),
                            ],
                        ),
                        color=(1, 0, 0),
                    )
                else:
                    bui.textwidget(
                        edit=text,
                        text=bui.Lstr(
                            resource='gatherWindow.' 'partyStatusJoinableText'
                        ),
                        color=(0, 1, 0),
                    )

    def _do_status_check(self) -> None:
        assert bui.app.classic is not None
        bui.textwidget(
            edit=self._host_status_text,
            color=(1, 1, 0),
            text=bui.Lstr(resource='gatherWindow.' 'partyStatusCheckingText'),
        )
        bui.app.classic.master_server_v1_get(
            'bsAccessCheck',
            {'b': bui.app.env.engine_build_number},
            callback=bui.WeakCallPartial(
                self._on_public_party_accessible_response
            ),
        )

    def _on_start_advertizing_press(self) -> None:
        from bauiv1lib.account.signin import show_sign_in_prompt

        plus = bui.app.plus
        assert plus is not None

        if plus.get_v1_account_state() != 'signed_in':
            show_sign_in_prompt()
            return

        name = cast(str, bui.textwidget(query=self._host_name_text))
        if name == '':
            bui.screenmessage(
                bui.Lstr(resource='internal.invalidNameErrorText'),
                color=(1, 0, 0),
            )
            bui.getsound('error').play()
            return
        bs.set_public_party_name(name)
        cfg = bui.app.config
        cfg['Public Party Name'] = name
        cfg.commit()
        bui.getsound('shieldUp').play()
        bs.set_public_party_enabled(True)

        # In GUI builds we want to authenticate clients only when
        # hosting public parties.
        bs.set_authenticate_clients(True)

        self._do_status_check()
        bui.buttonwidget(
            edit=self._host_toggle_button,
            label=bui.Lstr(
                resource='gatherWindow.makePartyPrivateText',
                fallback_resource='gatherWindow.stopAdvertisingText',
            ),
            on_activate_call=self._on_stop_advertising_press,
        )

    def _on_stop_advertising_press(self) -> None:
        bs.set_public_party_enabled(False)

        # In GUI builds we want to authenticate clients only when
        # hosting public parties.
        bs.set_authenticate_clients(False)
        bui.getsound('shieldDown').play()
        text = self._host_status_text
        if text:
            bui.textwidget(
                edit=text,
                text=bui.Lstr(
                    resource='gatherWindow.' 'partyStatusNotPublicText'
                ),
                color=(0.6, 0.6, 0.6),
            )
        bui.buttonwidget(
            edit=self._host_toggle_button,
            label=bui.Lstr(
                resource='gatherWindow.makePartyPublicText',
                fallback_resource='gatherWindow.startAdvertisingText',
            ),
            on_activate_call=self._on_start_advertizing_press,
        )

    def on_public_party_activate(self, party: PartyEntry) -> None:
        """Called when a party is clicked or otherwise activated."""
        self.save_state()
        uirow = self._ui_rows_by_party.get(id(party))
        uirow = uirow() if uirow is not None else None
        origin: tuple[float, float] | None = None
        if uirow is not None:
            # FIXME: Need to ask UIRow what it's 
            # main widget is instead of assuming.
            origin = uirow._button_widget.get_screen_space_center()
        PartyEntryWindow(
            party_entry=party,
            origin=origin
        )

    def set_public_party_selection(self, sel: Selection) -> None:
        """Set the sel."""
        if self._refreshing_list:
            return
        self._selection = sel
        self._have_user_selected_row = True

    def _on_max_public_party_size_minus_press(self) -> None:
        val = max(1, bs.get_public_party_max_size() - 1)
        bs.set_public_party_max_size(val)
        bui.textwidget(edit=self._host_max_party_size_value, text=str(val))

    def _on_max_public_party_size_plus_press(self) -> None:
        val = bs.get_public_party_max_size()
        val += 1
        bs.set_public_party_max_size(val)
        bui.textwidget(edit=self._host_max_party_size_value, text=str(val))
