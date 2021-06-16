import math
import random
from struct import pack, unpack

from matrixx import Vector, Matrix

import field
import weapons
from constants import FIELD_SIZE


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


class Player(Entity):
    TURN_ANGLE = 3  # 120 * this many degrees per second
    sin = math.sin(math.radians(TURN_ANGLE))
    cos = math.cos(math.radians(TURN_ANGLE))
    byte_len = 4*6 + 2*3 + 1*2
    MAX_ACCELERATION = 1
    ACCELERATION_FACTOR = 30
    FRICTION = 0.99  # set this to 0.99
    MAX_VELOCITY = 4  # set this to 4
    INIT_SIZE = 30
    SWITCH_COOL_DOWN = 60

    def __init__(self, field, name, x=FIELD_SIZE // 2, y=FIELD_SIZE // 2):
        super().__init__(x, y)
        self.field = field
        self.name = name
        self.velocity = Vector((1, 0))
        self.direction = Vector((1.0, 0.0))
        self.acceleration = 0

        self.target = self
        self.damage = 0
        self.points = 0
        self.cool_down = 0

        self.weapons = (
            weapons.Bullet, weapons.Laser, weapons.Flame,
            weapons.Mine, weapons.Minigun, weapons.Freeze,
            weapons.Meltdown
        )
        self.weapon_index = 0

    @property
    def score(self):
        return self.points - self.damage

    @property
    def size(self):
        return max(self.score, 0) + self.INIT_SIZE

    @property
    def health(self):
        return self.score + self.INIT_SIZE

    @property
    def weapon(self):
        return self.weapons[self.weapon_index]

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
        self.velocity = vector.limit(self.MAX_VELOCITY)

    def move(self):
        self.position += self.velocity
        self.position.limit_zero(FIELD_SIZE)
        self.velocity *= self.FRICTION

    def steer(self, turn, forward, shoot=0, weapon_switch=0):
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

        if weapon_switch and not self.cool_down:
            self.cool_down = self.SWITCH_COOL_DOWN
            self.weapon_index += weapon_switch
            self.weapon_index = self.weapon_index % len(self.weapons)

    def accelerate(self):
        if self.acceleration == 0:
            return
        accel = self.direction*(self.acceleration/self.ACCELERATION_FACTOR)
        self.velocity += accel
        self.velocity.limit(self.MAX_VELOCITY)
        self.acceleration *= self.FRICTION

    def is_colliding(self, other):
        if other is self:
            return False
        dist_squared = (self.position - other.position).length_squared
        if dist_squared < (self.size + other.size) ** 2:
            try:
                direction = (self.position - other.position).unit
                momentum = (other.velocity.length * other.size + self.velocity.length * self.size) / 2
                own_length = momentum/self.size
                other_length = momentum/other.size
                self.velocity = direction * own_length
                other.velocity = direction * -other_length

                '''
                # from here: wikipedia.org/wiki/Elastic_collision#Two-dimensional_collision_with_two_moving_objects
                direction = self.position-other.position  # todo check if this should be normalized
                length_squared = direction.length_squared
                dot_product = (self.velocity-other.velocity) @ direction
                total_mass = self.size + other.size
                precompute = direction * (2*dot_product/(total_mass*length_squared))
                print('pre', precompute)

                self.velocity -= other.size * precompute
                print('velocity', self.velocity)
                other.velocity += self.size * precompute
                '''

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
        spring_factor = 1
        if x_pos + size > FIELD_SIZE:
            self.velocity += Vector((FIELD_SIZE - (x_pos + size), 0)) * spring_factor
            # self.direction *= Vector((-1, 1))
            bounce = True
        elif x_pos - size < 0:
            self.velocity += Vector((-x_pos + size, 0)) * spring_factor
            # self.direction *= Vector((-1, 1))
            bounce = True

        if y_pos + size > FIELD_SIZE:
            self.velocity += Vector((0, FIELD_SIZE - (y_pos + size))) * spring_factor
            # self.direction *= Vector((1, -1))
            bounce = True
        elif y_pos - size < 0:
            self.velocity += Vector((0, -y_pos + size)) * spring_factor
            # self.direction *= Vector((1, -1))
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
        dmg = projectile.hit(self)
        self.damage += dmg
        return bool(dmg)

    def is_dead(self):
        if self.health < 0:
            x = random.randint(self.INIT_SIZE, FIELD_SIZE - self.INIT_SIZE)
            y = random.randint(self.INIT_SIZE, FIELD_SIZE - self.INIT_SIZE)
            self.__init__(self.field, self.name, x, y)
            return True
        return False

    def from_bytes(self, bytes, field):
        # current length  7*4 + 1*4 = 32 source_bytes
        float_offsets = (0, 4, 8, 12, 16, 20, 24)
        pos_x, pos_y, dir_x, dir_y, vel_x, vel_y = (
            unpack('f', bytes[start:end])[0]
            for start, end in zip(float_offsets, float_offsets[1:])
        )
        self.position = Vector((pos_x, pos_y))
        self.direction = Vector((dir_x, dir_y))
        self.velocity = Vector((vel_x, vel_y))
        #self.acceleration = acceleration

        dmg1, dmg2 = (bytes[pos] for pos in (24, 25))
        self.damage = (dmg1 << 8) + dmg2

        points1, points2 = (bytes[pos] for pos in (26, 27))
        self.points = (points1 << 8) + points2

        cd1, cd2 = (bytes[pos] for pos in (28, 29))
        self.cool_down = (cd1 << 8) + cd2

        target_id, self.weapon_index = (
            bytes[pos] for pos in (30, 31)
        )
        self.target = field.players[target_id]

    def to_bytes(self):
        # current length  7*4 + 2*2 + 1*2 = 34 source_bytes
        res = bytearray()
        res += pack('f', self.position[0])  # 4
        res += pack('f', self.position[1])  # 4
        res += pack('f', self.direction[0])  # 4
        res += pack('f', self.direction[1])  # 4
        res += pack('f', self.velocity[0])  # 4
        res += pack('f', self.velocity[1])  # 4
        res += self.damage.to_bytes(2, 'big')  # 2
        res += self.points.to_bytes(2, 'big')  # 2
        res += self.cool_down.to_bytes(2, 'big')  # 1
        res += self.target.name.to_bytes(1, 'big')  # 1
        res += self.weapon_index.to_bytes(1, 'big')  # 1
        return res
