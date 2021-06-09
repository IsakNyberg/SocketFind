import math
import random
from struct import pack, unpack

from matrixx import Vector, Matrix

import field
from constants import FIELD_SIZE

MAX_ACCELERATION = 1
ACCELERATION_FRACTION = 30
TURN_ANGLE = 2  # 120 * this many degrees per second
FRICTION = 0.99  # set this to 0.99
MAX_VELOCITY = 1  # set this to 4
SIZE = 20


def normalize(a, b):
    sum_ = math.sqrt(a * a + b * b)
    if sum_ == 0:
        return 0, 0
    return limit(a / sum_, 1), limit(b / sum_, 1)


def limit(n, lim):
    return max(min(lim, n), -lim)


def limit_zero(n, lim):
    return max(min(lim, n), 0)


class Entity:
    byte_len = 4 * 4 + 1 * 4

    def __init__(self, x, y):
        self.position = Vector((x, y))

    def get_dist_squared(self, pos):
        return (self.position - pos).length_squared


class Projectile(Entity):
    byte_len = 4*4 + 3 + 2 + 1*4

    def __init__(
            self, position, velocity,  damage=1, ttl=1000, size=3,
            colour=0xffffff, cool_down=100, recoil=1, shape=1, impact=1
    ):
        super().__init__(*position.to_tuple())
        self.velocity = velocity
        self.colour = colour
        self.time_to_live = ttl
        self.damage = damage
        self.size = size
        self.cool_down = cool_down
        self.recoil = recoil
        self.shape = shape  # 1=line, 2=circle
        self.impact = impact

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
        direction = player.position-self.position
        if direction.length_squared < player.size ** 2:  # todo size squared can be caches
            player.velocity += self.velocity * self.impact
            player.damage += self.damage
            self.time_to_live = 0
            return True
        else:
            return False

    def from_bytes(self, bytes):
        float_offsets = (0, 4, 8, 12, 16)
        pos_x, pos_y, vel_x, vel_y = (
            unpack('f', bytes[start:end])[0]
            for start, end in zip(float_offsets, float_offsets[1:])
        )
        self.position = Vector((pos_x, pos_y))
        self.velocity = Vector((vel_x, vel_y))

        colour1, colour2, colour3, ttl1, ttl2 = (
            bytes[pos] for pos in (16, 17, 18, 19, 20)
        )
        self.colour = (colour1 << 16) + (colour2 << 8) + colour3
        self.time_to_live = ttl1 << 8 + ttl2

        self.damage, self.size, self.recoil, self.shape = (
            bytes[pos] for pos in (21, 22, 23, 24)
        )

    def to_bytes(self):
        res = bytearray()
        res += pack('f', self.position[0])
        res += pack('f', self.position[1])
        res += pack('f', self.velocity[0])
        res += pack('f', self.velocity[1])
        res += self.colour.to_bytes(3, 'big')
        res += self.time_to_live.to_bytes(2, 'big')
        res += self.damage.to_bytes(1, 'big')
        res += int(self.size).to_bytes(1, 'big')
        res += self.recoil.to_bytes(1, 'big')
        res += self.shape.to_bytes(1, 'big')
        return res


class Bullet(Projectile):
    ttl = 500
    damage = 1
    colour = 0xe67f19
    cool_down = 100
    recoil = 30
    speed = 7
    size = 5
    shape = 1  #line

    def __init__(self, parent):
        super(Bullet, self).__init__(
            parent.position + parent.direction*parent.size*1.5,
            parent.direction * Bullet.speed,
            damage=Bullet.damage,
            ttl=Bullet.ttl,
            size=Bullet.size,
            colour=Bullet.colour,
            cool_down=Bullet.cool_down,
            recoil=Bullet.recoil,
        )


class Laser(Projectile):
    ttl = 50
    damage = 1
    colour = 0x66ff11
    cool_down = 20
    recoil = 0
    speed = 7
    size = 5
    shape = 1  #line

    def __init__(self, parent):
        super(Laser, self).__init__(
            parent.position + parent.direction*parent.size*1.5,
            parent.direction * Laser.speed,
            damage=Laser.damage,
            ttl=Laser.ttl,
            size=Laser.size,
            colour=Laser.colour,
            cool_down=Laser.cool_down,
            recoil=Laser.recoil,
            shape=Laser.shape,
        )


class Flame(Projectile):
    ttl = 150
    damage = 1
    colour = 0xfff0f0
    cool_down = 3
    recoil = 1
    speed = 3
    size = 5
    shape = 2  #circle

    def __init__(self, parent):
        super(Flame, self).__init__(
            parent.position + parent.direction*parent.size*1.5,
            parent.direction * Flame.speed,
            damage=Flame.damage,
            ttl=Flame.ttl,
            size=Flame.size,
            colour=Flame.colour,
            cool_down=Flame.cool_down,
            recoil=Flame.recoil,
            shape=Flame.shape,
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
        direction = player.position - self.position
        if direction.length_squared < player.size ** 2 + self.size ** 2:  # todo size squared can be caches
            player.velocity += (direction + self.velocity) * self.impact
            player.velocity.limit(MAX_VELOCITY)
            player.damage += self.damage
            return True
        else:
            return False


class Player(Entity):
    sin = math.sin(math.radians(TURN_ANGLE))
    cos = math.cos(math.radians(TURN_ANGLE))
    byte_len = 7*4 + 2*2 + 1*2

    def __init__(self, field, name, x=FIELD_SIZE // 2, y=FIELD_SIZE // 2):
        super().__init__(x, y)
        self.field = field
        self.name = name
        self.velocity = Vector((1, 0))
        self.direction = Vector((1.0, 0.0))
        self.acceleration = 0

        self._size = SIZE

        self.target = self
        self.damage = 0
        self.points = 0
        self.cool_down = 0

        self.weapon = Flame

    @property
    def score(self):
        return self.points - self.damage

    @property
    def size(self):
        return max(self.score, 0) + SIZE

    @property
    def front(self):
        return self.points - self.damage

    def set_position(self, x=-1, y=-1):
        if x == -1 and y == -1:
            x = random.randint(self.size, FIELD_SIZE - self.size)
            y = random.randint(self.size, FIELD_SIZE - self.size)
        vector = Vector((limit_zero(x, FIELD_SIZE), limit_zero(y, FIELD_SIZE)))
        self.position = vector

    def set_velocity(self, x=-1, y=-1):
        if x == -1 and y == -1:
            x = random.randint(-FIELD_SIZE, FIELD_SIZE)
            y = random.randint(-FIELD_SIZE, FIELD_SIZE)
        vector = Vector((x, y))
        self.velocity = vector.limit(MAX_VELOCITY)

    def move(self):
        self.position += self.velocity
        self.position.limit_zero(FIELD_SIZE)
        self.velocity *= FRICTION

    def steer(self, turn, forward, shoot=0):
        if turn > 0:  # anti clockwise
            rotation_matrix = Matrix(((Player.cos, Player.sin), (-Player.sin, Player.cos)))
        elif turn < 0:  # clockwise
            rotation_matrix = Matrix(((Player.cos, -Player.sin), (Player.sin, Player.cos)))
        else:
            rotation_matrix = None

        if rotation_matrix is not None:
            self.direction = rotation_matrix @ self.direction
            self.direction = self.direction.unit

        if forward < 0:
            self.velocity *= 0.9
        elif forward > 0:
            self.acceleration = 1
        else:
            self.acceleration = 0

        if shoot:
            self.shoot()

    def accelerate(self):
        if self.acceleration == 0:
            return
        acceleration = self.direction * (self.acceleration / ACCELERATION_FRACTION)
        self.velocity += acceleration
        self.velocity.limit(MAX_VELOCITY)
        self.acceleration *= FRICTION

    def is_colliding(self, other):
        if other is self:
            return False
        dist_squared = (self.position - other.position).length_squared
        if dist_squared < (self.size + other.size) ** 2:
            try:
                new_velocity = (self.position - other.position).unit
                new_length = (self.velocity.length + other.velocity.length) / 2
                self.velocity = new_velocity * new_length
                other.velocity = new_velocity * -new_length
            except ZeroDivisionError:
                print('Warning: Zero division in ball collision.')
                pass
            '''
            if self.target is other and not other.cool_down:
                self.points += 1
                other.damage += 1
                # self.cool_down = 0xff  when you tag you don't go on cool down
                other.cool_down = 0xff
                return 2
            return 1
            '''
            return True
        else:
            return False

    def new_target(self, players):
        self.target = self
        if len(players) < field.MIN_PLAYERS:
            return self

        tries = 0 if field.MIN_PLAYERS < len(players) else len(players)
        while self.target == self or (self.target.target is self and tries < len(players)):
            self.target = players[random.randint(0, len(players)-1)]
            tries += 1
        return self.target

    def wall_bounce(self):
        bounce = False
        x_pos = self.position[0]
        y_pos = self.position[1]
        size = self.size
        spring_factor = 0.001
        if x_pos + size > FIELD_SIZE:
            self.velocity += Vector((FIELD_SIZE - (x_pos + size), 0)) * spring_factor
            #self.direction *= Vector((-1, 1))
            bounce = True
        elif x_pos - size < 0:
            self.velocity += Vector((-x_pos + size, 0)) * spring_factor
            #self.direction *= Vector((-1, 1))
            bounce = True

        if y_pos + size > FIELD_SIZE:
            self.velocity += Vector((0, FIELD_SIZE - (y_pos + size))) * spring_factor
            #self.direction *= Vector((1, -1))
            bounce = True
        elif y_pos - size < 0:
            self.velocity += Vector((0, -y_pos + size)) * spring_factor
            #self.direction *= Vector((1, -1))
            bounce = True
        #if bounce:
        #    self.velocity.limit(MAX_VELOCITY)
        return bounce

    def shoot(self):
        if self.cool_down:
            return
        self.cool_down = self.weapon.cool_down
        self.velocity += self.direction * -self.weapon.recoil*0.1
        self.field.new_projectile(self.weapon(self))

    def is_hit(self, projectile):
        return projectile.hit(self)

    def from_bytes(self, bytes, field):
        # current length  7*4 + 1*4 = 32 bytes
        float_offsets = (0, 4, 8, 12, 16, 20, 24, 28)
        pos_x, pos_y, dir_x, dir_y, vel_x, vel_y, acceleration = (
            unpack('f', bytes[start:end])[0]
            for start, end in zip(float_offsets, float_offsets[1:])
        )
        self.position = Vector((pos_x, pos_y))
        self.direction = Vector((dir_x, dir_y))
        self.velocity = Vector((vel_x, vel_y))
        self.acceleration = acceleration

        dmg1, dmg2, points1, points2 = (
            bytes[pos] for pos in (28, 29, 30, 31)
        )
        self.damage = dmg1 << 8 + dmg2
        self.points = points1 << 8 + points2
        target_id, self.cool_down = (
            bytes[pos] for pos in (32, 33)
        )
        self.target = field.players[target_id]

    def to_bytes(self):
        # current length  7*4 + 2*2 + 1*2 = 34 bytes
        res = bytearray()
        res += pack('f', self.position[0])  # 4
        res += pack('f', self.position[1])  # 4
        res += pack('f', self.direction[0])  # 4
        res += pack('f', self.direction[1])  # 4
        res += pack('f', self.velocity[0])  # 4
        res += pack('f', self.velocity[1])  # 4
        res += pack('f', self.acceleration)  # 4
        res += self.damage.to_bytes(2, 'big')  # 2
        res += self.points.to_bytes(2, 'big')  # 2
        res += self.target.name.to_bytes(1, 'big')  # 1
        res += self.cool_down.to_bytes(1, 'big')  # 1
        return res
