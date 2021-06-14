import math
import random
from struct import pack, unpack, error

from matrixx import Vector


def from_bytes(players, source_bytes):
    parent = players[source_bytes[0]]
    projectile = WEAPON_LOOKUP[source_bytes[1]](parent)
    projectile.from_bytes(source_bytes[2:])
    return projectile


class Weapon:
    WEAPON_ID = 0
    byte_len = 1 + 1 + 4*4 + 3 + 2 + 1
    cool_down = 100
    recoil = 1

    def __init__(
            self, parent_index, position, velocity,  damage=1, ttl=1000,
            size=3, colour=0xffffff, impact=1,
    ):
        self.parent_index = parent_index
        self.position = position
        self.velocity = velocity
        self.colour = colour
        self.time_to_live = ttl
        self.damage = damage
        self.size = size
        self.impact = impact

    def get_dist_squared(self, pos):
        return (self.position - pos).length_squared

    def tick(self):
        self.position += self.velocity
        if self.time_to_live > 0:
            self.time_to_live -= 1
            return False
        else:
            return True

    def colour_tuple(self):
        r = ((self.colour >> 16) & 0xff) / 255
        g = ((self.colour >> 8) & 0xff) / 255
        b = (self.colour & 0xff) / 255
        return r, g, b

    def hit(self, player):
        if player.name == self.parent_index:
            return False
        direction = player.position-self.position
        direction_sq = direction.length_squared
        player_size_sq = player.size ** 2
        if direction_sq < player_size_sq:  # todo size squared can be cached
            player.velocity += (self.velocity * self.impact)
            player.damage += self.damage
            self.time_to_live = 0
            return True
        else:
            return False

    def from_bytes(self, source_bytes):
        float_offsets = (0, 4, 8, 12, 16)
        pos_x, pos_y, vel_x, vel_y = (
            unpack('f', source_bytes[start:end])[0]
            for start, end in zip(float_offsets, float_offsets[1:])
        )
        self.position = Vector((pos_x, pos_y))
        self.velocity = Vector((vel_x, vel_y))

        colour1, colour2, colour3, ttl1, ttl2 = (
            source_bytes[pos] for pos in (16, 17, 18, 19, 20)
        )
        self.colour = (colour1 << 16) + (colour2 << 8) + colour3
        self.time_to_live = ttl1 << 8 + ttl2

        self.size = source_bytes[21]

    def to_bytes(self):
        res = bytearray()
        res += self.parent_index.to_bytes(1, 'big')
        res += self.WEAPON_ID.to_bytes(1, 'big')
        res += pack('f', self.position[0])
        res += pack('f', self.position[1])
        res += pack('f', self.velocity[0])
        res += pack('f', self.velocity[1])
        res += self.colour.to_bytes(3, 'big')
        res += self.time_to_live.to_bytes(2, 'big')
        res += int(self.size).to_bytes(1, 'big')
        return res


class Bullet(Weapon):
    WEAPON_ID = 1
    cool_down = 100
    recoil = 1
    shape = 1

    def __init__(self, parent):
        super(Bullet, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size*1.5,
            parent.direction * 7,
            damage=1,
            ttl=360,
            size=5,
            colour=0xe67f19,
        )


class Laser(Weapon):
    WEAPON_ID = 2
    cool_down = 20
    recoil = 0
    shape = 1

    def __init__(self, parent):
        super(Laser, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size*1.5,
            parent.direction * 7,
            damage=1,
            ttl=60,
            size=5,
            colour=0x66ff11,
        )


class Flame(Weapon):
    WEAPON_ID = 3
    cool_down = 3
    recoil = 1
    shape = 2

    def __init__(self, parent):
        super(Flame, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size*1.2,
            parent.direction * 3,
            damage=1,
            ttl=150,
            size=5,
            colour=0xfff0f0,
        )

    def tick(self):
        friction = 0.99
        size_increase = 0.3
        self.position += self.velocity
        self.velocity *= friction
        self.size += size_increase
        r = max((self.colour & 0xff0000) - 0x010000, 0x001000)
        g = max((self.colour & 0x00ff00) - 0x000200, 0x000100)
        b = max((self.colour & 0x0000ff) - 0x000004, 0x000001)
        self.colour = r | g | b
        if self.time_to_live > 0:
            self.time_to_live -= 1
            return False
        else:
            return True

    def hit(self, player):
        direction = player.position-self.position
        direction_sq = direction.length_squared
        if direction_sq < player.size ** 2 + self.size ** 2:
            player.velocity += direction.unit*self.velocity.length*self.impact
            player.damage += self.damage
            self.time_to_live = 0
            return True
        else:
            return False


class Mine(Weapon):
    WEAPON_ID = 4
    DURATION = 120 * 10
    SAFE_DURATION = DURATION * 0.8
    DETECTION_RADIUS = 600
    cool_down = 120
    recoil = 1
    shape = 2

    def __init__(self, parent):
        super(Mine, self).__init__(
            parent.name,
            parent.position - parent.direction*parent.size*1.2,
            parent.direction * 1,
            damage=1,
            ttl=Mine.DURATION,
            size=3,
            colour=0xffffff,
        )

    def tick(self):
        if self.time_to_live <= int(Mine.DURATION * 0.05):
            if self.time_to_live == int(Mine.DURATION * 0.05):
                self.colour = 0x000000
            else:
                r = min((self.colour & 0xff0000) + 0x050000, 0xff0000)
                g = min((self.colour & 0x00ff00) + 0x000500, 0x00ff00)
                b = min((self.colour & 0x0000ff) + 0x000007, 0x0000ff)
                self.colour = r | g | b
                self.size += 2
        elif self.time_to_live < int(Mine.DURATION * 0.2):
            self.colour = 0xf00000
        else:
            self.colour = 0xffffff

        if self.time_to_live > 0:
            self.time_to_live -= 1
            return False
        else:
            return True

    def hit(self, player):
        if self.time_to_live > int(Mine.SAFE_DURATION):
            return False

        direction = player.position - self.position
        if direction.length_squared < Mine.DETECTION_RADIUS ** 2:
            self.time_to_live = min(int(Mine.DURATION * 0.1), self.time_to_live)

        if self.time_to_live == 0:
            if direction.length_squared < (player.size + self.size) ** 2:
                player.velocity += direction.unit * 30
                return True

        return False



WEAPON_LOOKUP = {
    #0: Weapon,  # this one should not be used
    1: Bullet,
    2: Laser,
    3: Flame,
    4: Mine,
}
