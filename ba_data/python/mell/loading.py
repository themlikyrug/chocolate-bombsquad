"""Activity that shows a nice little loading 
screen while everything happens."""
from __future__ import annotations

from bascenev1lib.actor.background import Background
import bascenev1 as bs

class LoadingSession(bs.Session):
    def __init__(self) -> None:
        super().__init__([])
        self._locked = False
        self.setactivity(bs.newactivity(LoadingActivity))

    def on_player_request(self, player: bs.SessionPlayer):
        # Reject all player requests.
        return False

class LoadingActivity(bs.Activity[bs.Player, bs.Team]):
    def on_begin(self):
        Background(show_logo=False).autoretain()
        v = 60
        spinner_size = 160
        node = bs.newnode(
            'image',
            attrs={
                'texture': bs.gettexture('spinner'),
                'scale': (spinner_size, spinner_size),
                'position': (0, v),
            }
        )
        bs.animate(
            node,
            'rotate',
            {
                0: 0,
                1: -360,
            },
            loop=True,
        )
        v -= spinner_size + 10
        bs.newnode(
            'text',
            attrs={
                'text': 'The game is preparing\nnecessary stuff; please wait...',
                'flatness': 0.5,
                'shadow': 0.7,
                'h_align': 'center',
                'scale': 1.6,
                'position': (0, v),
            }
        )
        v -= 60
        node = bs.newnode(
            'text',
            attrs={
                'text': (
                    'If this is taking too long, a bug may have occured; restart the game.'
                    '\nThis is not something I can really fix, it depends on YOUR computer.'
                ),
                'flatness': 0.5,
                'shadow': 0.7,
                'h_align': 'center',
                'v_align': 'top',
                'scale': 0.8,
                'position': (0, v),
            }
        )
        bs.animate(
            node,
            'opacity',
            {
                5: 0,
                5.5: 0.5,
            },
        )


