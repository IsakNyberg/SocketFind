from enum import Flag, auto


class Action(Flag):
    FWD = auto()
    LEFT = auto()
    STOP = auto()
    RIGHT = auto()
    SHOOT = auto()


KEYS_BINDINGS = {
    b'w': Action.FWD,
    b'a': Action.LEFT,
    b's': Action.STOP,
    b'd': Action.RIGHT,
    b' ': Action.SHOOT,
}


CUR_ACTION = Action(0)


def set_key(key, *args):
    global CUR_ACTION
    act = KEYS_BINDINGS.get(key.lower(), Action(0))
    CUR_ACTION |= act


def unset_key(key, *args):
    global CUR_ACTION
    act = KEYS_BINDINGS.get(key.lower(), Action(0))
    CUR_ACTION &= ~act


def forward_status():
    return (Action.FWD in CUR_ACTION) - (Action.STOP in CUR_ACTION)


def turn_status():
    return (Action.LEFT in CUR_ACTION) - (Action.RIGHT in CUR_ACTION)


def shoot_status():
    return Action.SHOOT in CUR_ACTION


def set_action_value(value):
    global CUR_ACTION
    CUR_ACTION = Action(value)


def get_action_value():
    return CUR_ACTION.value.to_bytes(1, 'big')


def get_actions_tuple():
    return turn_status(), forward_status(), shoot_status()
