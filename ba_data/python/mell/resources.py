"""Useful resources and functions"""

def get_festivity():
    """Gets the current festivity 
    (april fools, christmas, etc)"""
    from datetime import date
    import bauiv1 as bui
    plus = bui.app.plus
    today = date.today()
    day = today.day
    month = today.month
    christmas = month == 12 and day == 25
    easter = plus.get_v1_account_misc_read_val('easter', False)
    if christmas:
        return "christmas"
    if easter:
        return "easter"

def open_link(url: str):
    from mell.ui.open_link import OpenLinkWindow
    OpenLinkWindow(url)

def clamp(num, min_val, max_val):
    return max(min(num, max_val), min_val)

def hex_to_color(hex_color: str) -> tuple:
    # Remove the '#' from the string if provided.
    if hex_color.startswith('#'):
        hex_color = hex_color.lstrip('#')
    # Check if this has a valid length.
    hexlength = len(hex_color)
    if not hexlength in [6, 8]:
        raise ValueError(f'Invalid HEX color provided: "{hex_color}"')

    # Convert the hex bytes to their true byte form.
    ar, ag, ab, aa = (
        (int.from_bytes(bytes.fromhex(hex_color[0:2]))),
        (int.from_bytes(bytes.fromhex(hex_color[2:4]))),
        (int.from_bytes(bytes.fromhex(hex_color[4:6]))),
        (
            (int.from_bytes(bytes.fromhex(hex_color[6:8])))
            if hexlength == 8
            else None
        ),
    )
    # Divide all numbers by 255 and return.
    nr, ng, nb, na = (
        x / 255 if x is not None else None for x in (ar, ag, ab, aa)
    )
    return (nr, ng, nb, na) if aa is not None else (nr, ng, nb)

def show_notification(
    top_text: str = 'Notification',
    bottom_text: str = 'Bottom Text',
    icon: str | dict | None = None,
    mini_icon: str | None = None,
    sound: str = 'notification',
):
    """Shows a notification.
    important determines whether the notification
    is a normal, important notification, or a 
    non-important notification."""

    import bascenev1 as bs
    import textwrap

    session = bs.get_foreground_host_session()
    if not session:
        return

    with session.context:

        # keep track of notifications
        if not hasattr(bs.app, 'notifications'):
            bs.app.notifications = {}

        def _get_free_slot(entries: dict) -> int:
            slot = 0
            while slot in entries:
                slot += 1
            return slot

        # simple text wrapping
        wrap_width = 34
        wrapped_bottom = textwrap.fill(bottom_text, width=wrap_width)
        line_count = wrapped_bottom.count('\n') + 1

        slot = _get_free_slot(bs.app.notifications)
        bs.app.notifications[slot] = True

        width = 320

        # dynamically resize window
        extra_lines = max(0, line_count - 2)
        height = 70 + (extra_lines * 23)

        base_x = 470
        base_y = -40

        # account for resized notifications
        for i in range(slot):
            base_y -= 75

        base_y -= extra_lines * 8
        extra_box_y = extra_lines * 10

        nodes: list[bs.Node] = []
        transitioning = False
        front = True

        # play a sound based on importance
        bs.getsound(sound).play(volume=1.5)

        # background
        bg = bs.newnode(
            'image',
            attrs={
                'texture': bs.gettexture('softRect'),
                'position': (base_x, base_y - extra_box_y),
                'scale': (width, height),
                'color': (0.1, 0.1, 0.1),
                'opacity': 0.85,
                'attach': 'topCenter',
                'front': front,
            },
        )
        nodes.append(bg)

        # title
        title = bs.newnode(
            'text',
            attrs={
                'text': top_text,
                'position': (base_x - 110, base_y + 20),
                'scale': 1.1,
                'maxwidth': 150,
                'color': (1.0, 1.0, 1.0, 1.0),
                'h_align': 'left',
                'v_align': 'center',
                'shadow': 1.0,
                'flatness': 0.0,
                'v_attach': 'top',
                'front': front,
            },
        )
        nodes.append(title)

        # description
        desc = bs.newnode(
            'text',
            attrs={
                'text': wrapped_bottom,
                'position': (base_x - 110, base_y + 7),
                'scale': 0.9,
                'maxwidth': 270,
                'color': (0.85, 0.85, 0.85, 1.0),
                'h_align': 'left',
                'v_align': 'top',
                'shadow': 0.8,
                'flatness': 0.0,
                'v_attach': 'top',
                'front': front,
            },
        )
        nodes.append(desc)

        # main icon
        if icon:
            icon_node = bs.newnode(
                'image',
                attrs={
                    'texture': bs.gettexture(icon),
                    'position': (base_x - 145, base_y),
                    'scale': (42, 42),
                    'attach': 'topCenter',
                    'front': front,
                },
            )
            nodes.append(icon_node)

            # mini icon
            if mini_icon:
                mini = bs.newnode(
                    'image',
                    attrs={
                        'texture': bs.gettexture(mini_icon),
                        'position': (base_x - 125, base_y - 18),
                        'scale': (20, 20),
                        'attach': 'topCenter',
                        'front': front,
                    },
                )
                nodes.append(mini)

        # animate in
        for node in nodes:
            time = 0.05

            if node.getnodetype() == 'text':
                bs.animate(node, 'opacity', {
                    0.0: 0.0,
                    time: 1.0,
                })
            else:
                bs.animate(node, 'opacity', {
                    0.0: 0.0,
                    time: node.opacity,
                })

            bs.animate_array(
                node,
                'position',
                2,
                {
                    0.0: (node.position[0], node.position[1] + 20),
                    time: node.position,
                }
            )

        def trans_out():
            nonlocal transitioning

            if transitioning:
                return

            transitioning = True

            bs.app.notifications.pop(slot, None)

            for node in nodes:
                try:
                    current = getattr(node, 'opacity', 1.0)
                    time = 0.3

                    bs.animate(node, 'opacity', {
                        0.0: current,
                        time: 0.0,
                    })

                    bs.timer(time, node.delete)

                except Exception:
                    pass

        # auto-remove
        bs.timer(4.0, trans_out)
