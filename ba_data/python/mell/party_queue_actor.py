"""Class that handles displaying current party queue"""
import bascenev1 as bs
import bauiv1 as bui
import babase as ba

class PartyQueueActor:
    def __del__(self):
        self._delete()
        self._dead = True
        
    def __init__(self, delegate):
        self._dead = False
        self.node = None
        self._delegate = delegate
        self._nodes = []
        # front determines whether
        # we're appearing above ui
        # i dont know why this exists
        self._front = True
        self._scale = 0.5
        self._transitioning = False
        self._size = (700 * self._scale, 200 * self._scale)
        # screen pos... i guess
        screen_space = bui.get_virtual_screen_size()
        screen_space = (
            screen_space[0] * 0.5,
            screen_space[1] * 0.5,
        )
        self._pos = (
            screen_space[0] - (self._size[0] * 0.5),
            -screen_space[1] + 60
        )
        self._recreate()
    
    def _delete(self):
        if self.node:
            self.node.delete()
    
    def exists(self):
        return bool(self.node)
    
    def _recreate(self):
        session = bs.get_foreground_host_session()
        if not session:
            return
        with session.context:
            if self.node:
                self.node.delete()
            for node in self._nodes:
                if node:
                    node.delete()
            self._nodes.clear()
            self.node = bs.newnode(
                'image',
                attrs={
                    'texture': bs.gettexture('softRect2'),
                    'scale': self._size,
                    'front': self._front,
                    'color': (0.1, 0.1, 0.1),
                    'position': self._pos,
                }
            )
            # for the spinner's scale,
            # we wanna take the height of our window 
            # minus how much big the title text is (and extra y just incase)
            spinner_scale = (
                self._size[1] - 30,
                self._size[1] - 30,
            )
            thisnode = self._spinner = bs.newnode(
                'image',
                attrs={
                    'texture': bs.gettexture('spinner'),
                    'scale': spinner_scale,
                    'front': self._front,
                    'position': (
                        self._pos[0] - self._size[0] * 0.5 + 50,
                        self._pos[1],
                    ),
                }
            )
            bs.animate(
                thisnode,
                'rotate',
                {
                    0: 0,
                    1.0: -360,
                },
                loop=True,
            )
            
            self._nodes.append(thisnode)
            thisnode = self._title_text = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'position': (
                        self._pos[0] - self._size[0] * 0.5 + 100,
                        self._pos[1] + self._size[1] - 90,
                    ),
                    'scale': self._scale + 0.4,
                    'maxwidth': self._size[0] - 100,
                    'front': self._front,
                }
            )
            self._nodes.append(thisnode)
            thisnode = self._status_text = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'position': (
                        self._pos[0] - self._size[0] * 0.5 + 100,
                        self._pos[1] + self._size[1] - 115,
                    ),
                    'scale': self._scale + 0.3,
                    'maxwidth': self._size[0] * 0.7,
                    'front': self._front,
                    'color': (0.8, 0.8, 0.8),
                }
            )
            self._nodes.append(thisnode)
            thisnode = self._other_guys_text = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'position': (
                        self._pos[0] - self._size[0] * 0.5 + 100,
                        self._pos[1] + self._size[1] - 140,
                    ),
                    'scale': self._scale + 0.3,
                    'maxwidth': self._size[0] * 0.65,
                    'front': self._front,
                    'color': (0.75, 0.75, 0.75),
                    'opacity': 0,
                }
            )
            self._nodes.append(thisnode)
            self._transitioning = True
            for node in self._nodes:
                bs.animate(
                    node,
                    'opacity',
                    {
                        0: 0,
                        0.6: node.opacity,
                    }
                )
        def setfalse():
            self._transitioning = False
        ba.apptimer(0.6, setfalse)
    
    def update(self):
        state = self._delegate._state
        other_guys = self._delegate._other_queue_guys
        # FIXME: don't do this
        if not self._transitioning:
            for node in self._nodes:
                if node:
                    node.opacity = 0
        if state == 'connecting':
            self._status_text.opacity = 1
            self._status_text.text = 'Connecting...'
        elif state == 'waiting_till_connect':
            self._status_text.opacity = 1
            self._status_text.text = 'Queued...'
        elif state == 'connected':
            self._status_text.opacity = 1
            self._status_text.text = 'Connected!'
        elif state == 'party_full':
            self._status_text.opacity = 1
            self._status_text.text = 'Party is full; waiting...'
        elif state == 'party_reject':
            self._status_text.opacity = 1
            self._status_text.text = 'Party rejected connect; waiting...'
        if other_guys:
            names = list(guy.name for guy in other_guys)
            plist = ', '.join(names)
            self._other_guys_text.opacity = 1
            self._other_guys_text.text = f'behind {plist}'
        
        if not self._transitioning:
            self._spinner.opacity = 1
            self._title_text.opacity = 1
        self._title_text.text = self._delegate._party_name