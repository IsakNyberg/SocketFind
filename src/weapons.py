import math
import random
import struct
from struct import pack, unpack, error

import matrixx
from matrixx import Vector
from matrixx import M2


def from_bytes(players, source_bytes):
    parent = players[source_bytes[0]]
    projectile = WEAPON_LOOKUP[source_bytes[1]](parent)
    projectile.from_bytes(source_bytes[2:])
    return projectile


index = 0
spread_pattern = tuple(random.randint(0, 180) for _ in range(360*10))
def spread_matrix(angle):
    global index
    index = (index + 1) % 300
    angle = (spread_pattern[index] % angle * 2) - angle
    return M2.rot(math.radians(angle))


class Weapon:
    WEAPON_ID = 0
    byte_len = 1 + 1 + 4*4 + 3 + 2 + 1
    cool_down = 100
    recoil = 1

    def __init__(
            self, parent_index, position, velocity,  damage=1, ttl=1000,
            size=3, colour=0xffffff, impact=1.0, spread_angle=0
    ):
        self.parent_index = parent_index
        self.position = position
        self.velocity = velocity
        self.colour = colour
        self.time_to_live = ttl
        self.damage = damage
        self.size = size
        self.impact = impact

        if spread_angle:
            self.velocity = spread_matrix(spread_angle) @ self.velocity

    def get_dist_squared(self, pos):
        return (self.position - pos).length_squared

    def tick(self):
        self.position += self.velocity
        if self.time_to_live > 0:
            self.time_to_live -= 1
            return False
        else:
            return True

    def hit(self, player):
        if player.name == self.parent_index:
            return False
        direction = player.position-self.position
        direction_sq = direction.length_squared
        player_size_sq = player.size ** 2
        if direction_sq < player_size_sq:  # todo size squared can be cached
            player.velocity += (self.velocity * self.impact)
            self.time_to_live = 0
            return self.damage
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
        self.time_to_live = (ttl1 << 8) + ttl2

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
    recoil = 15
    shape = 1

    def __init__(self, parent):
        super(Bullet, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size,
            parent.direction * 7,
            damage=10,
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
            parent.position + parent.direction*parent.size,
            parent.direction * 7,
            damage=5,
            ttl=60,
            size=5,
            colour=0x66ff11,
            spread_angle=2
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
            parent.direction * 3 + parent.velocity.limit(2),
            damage=2,
            ttl=150,
            size=5,
            colour=0xfff0f0,
            spread_angle=4
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
            self.time_to_live = 0
            return self.damage
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
            parent.direction * 1 + parent.velocity,
            damage=25,
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
            return 0

        direction = player.position - self.position
        if direction.length_squared < Mine.DETECTION_RADIUS ** 2:
            self.time_to_live = min(int(Mine.DURATION * 0.1), self.time_to_live)

        if self.time_to_live == 0:
            if direction.length_squared < (player.size + self.size) ** 2:
                player.velocity += direction.unit * 30
                return self.damage

        return 0


class Minigun(Weapon):
    WEAPON_ID = 5
    cool_down = 0
    recoil = 0
    shape = 1

    def __init__(self, parent):
        super(Minigun, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size,
            parent.direction * 6 + parent.velocity,
            damage=1,
            ttl=50,
            size=1,
            colour=0xe67f19,
            spread_angle=parent.velocity.length_squared + 6,
            impact=0.5
        )


class Freeze(Weapon):
    WEAPON_ID = 6
    cool_down = 120
    recoil = 0
    shape = 2

    def __init__(self, parent):
        super(Freeze, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size,
            parent.direction * 6 + parent.velocity,
            damage=0,
            ttl=120*3,
            size=10,
            colour=0x5084ac,
        )

    def hit(self, player):
        if player.name == self.parent_index:
            return 0

        direction = player.position - self.position
        if direction.length_squared < (self.size + player.size) ** 2:
            self.velocity = Vector((0, 0))
            self.position = player.position
            self.colour = 0xd0d0ff
            self.size = player.size
            self.time_to_live -= 1
            player.velocity *= 0.94
            return False  # todo chance this back to True when dmg is used
        return 0


class Meltdown(Weapon):
    WEAPON_ID = 7
    cool_down = 1 << 8
    recoil = 0
    shape = 2
    MAX_REACH = 800

    def __init__(self, parent):
        super(Meltdown, self).__init__(
            parent.name,
            parent.position + parent.direction*parent.size,
            parent.velocity,
            damage=parent.score + parent.size + 10,
            ttl=1 << 8,
            size=1,
            colour=0x000000,
        )

    def tick(self):
        size_increase = 0.3
        self.size += size_increase
        r = min((self.colour & 0xff0000) + 0x010000, 0xff0000)
        g = min((self.colour & 0x00ff00) + 0x000300, 0x00ff00)
        b = min((self.colour & 0x0000ff) + 0x000002, 0x0000ff)
        self.colour = r | g | b
        if self.time_to_live > 0:
            self.time_to_live -= 1
            return False
        else:
            return True

    def hit(self, player):
        if player.name == self.parent_index:
            self.position = player.position
            #player.velocity = self.velocity

        if self.time_to_live == 0:
            direction = self.position - player.position
            if direction.length_squared < (self.size + player.size) ** 2:
                return self.damage
        return 0


WEAPON_LOOKUP = {
    #0: Weapon,  # this one should not be used
    1: Bullet,
    2: Laser,
    3: Flame,
    4: Mine,
    5: Minigun,
    6: Freeze,
    7: Meltdown,
}
