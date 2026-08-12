"""UI that asks the user whether they 
want to continue to a web-browser."""
import bauiv1 as bui
import babase as ba
import random

class OpenLinkWindow(bui.Window):
    def __init__(self, url: str):
        self._url = url
        transition = 'in_scale'
        width = 700
        height = 270
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
        button_y = 30
        v = height - 30
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, v),
            size=(0, 0),
            text=bui.Lstr(r="willOpenLinkText"),
            scale=1.1,
            maxwidth=width * 0.9,
            h_align="center",
            v_align="top",
        )
        v -= 70
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, v),
            size=(0, 0),
            text=bui.Lstr(v=url),
            scale=1.4,
            maxwidth=width * 0.9,
            color=(0.1, 0.8, 1),
            h_align="center",
            v_align="center",
        )
        v -= 50
        # hehehehe
        self._proceed = random.random() < 0.07
        text = "noelleIsReal1225" if self._proceed else "warningContinueText"
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, v),
            size=(0, 0),
            text=bui.Lstr(r=text),
            scale=1.1,
            maxwidth=width * 0.9,
            h_align="center",
            v_align="center",
        )
        text = 'stopText' if self._proceed else 'backText' 
        btn = bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(button_spacing - (button_width * 0.5), button_y),
            size=(button_width, button_height),
            text_scale=1.1,
            label=bui.Lstr(r=text),
            on_activate_call=self.cancel,
        )
        bui.containerwidget(
            edit=self._root_widget,
            cancel_button=btn,
        )
        text = 'proceedText' if self._proceed else 'continueText'
        bui.buttonwidget(
            parent=self._root_widget,
            autoselect=False,
            position=(width - button_spacing - (button_width * 0.5), button_y),
            size=(button_width, button_height),
            text_scale=1.1,
            label=bui.Lstr(r=text),
            on_activate_call=self.agree,
        )
    
    def cancel(self):
        if self._proceed:
            bui.getsound('secrets/ominous_cancel').play()
        self.close()
    
    def close(self):
        bui.containerwidget(
            edit=self._root_widget,
            transition='out_scale',
        )
    
    def agree(self):
        if self._proceed:
            bui.getsound('secrets/ominous').play()
        self.close()
        ba.open_url(self._url)