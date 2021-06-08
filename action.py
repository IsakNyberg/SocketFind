from enum import Flag, auto


class Action(Flag):
    FWD = auto()
    LEFT = auto()
    STOP = auto()
    RIGHT = auto()
    SHOOT = auto()


KEYS_BINDINGS = {
    ord('w'): Action.FWD,
    ord('a'): Action.LEFT,
    ord('s'): Action.STOP,
    ord('d'): Action.RIGHT,
    ord(' '): Action.SHOOT,
}


class ActionStatus:
    def __init__(self):
        self.cur = Action(0)

    def set_key(self, key, *args):
        self.cur |= KEYS_BINDINGS.get(key, Action(0))

    def unset_key(self, key, *args):
        self.cur &= ~KEYS_BINDINGS.get(key, Action(0))

    def set_action_value(self, value):
        self.cur = Action(value)

    @property
    def as_byte(self):
        return self.cur.value.to_bytes(1, 'big')

    @property
    def as_tuple(self):
        return (
            (Action.LEFT in self.cur) - (Action.RIGHT in self.cur),
            (Action.FWD in self.cur) - (Action.STOP in self.cur),
            Action.SHOOT in self.cur,
        )

    def update_from_pygame(self, keys):
        for (n, act) in KEYS_BINDINGS.items():
            if keys[n]:
                self.cur |= act
            else:
                self.cur &= ~act
