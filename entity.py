import math
import random
import field

from struct import pack, unpack
from matrixx import Vector, Matrix

MAX_ACCELERATION = 1
ACCELERATION_FRACTION = 30
TURN_angle = 2  # 120 * this many degrees per second
FRICTION = 0.99  # set this to 0.99
MAX_VELOCITY = 1  # set this to 4
MAX_POSITION = 2000
SIZE = 20
GRAVITY_FRACTION = 70


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
    byte_len = 4*4 + 1*4

    def __init__(self, position, velocity,  damage=1, range=1024):
        super().__init__(*position.to_tuple())
        self.velocity = velocity
        self.time_to_live = range
        self.damage = damage
        self.size = 3

    def tick(self):
        self.position += self.velocity
        if self.time_to_live:
            self.time_to_live -= 1
        else:
            return True

    def from_bytes(self, bytes):
        float_offsets = (0, 4, 8, 12, 16)
        pos_x, pos_y, vel_x, vel_y = (
            unpack('f', bytes[start:end])[0]
            for start, end in zip(float_offsets, float_offsets[1:])
        )
        self.position = Vector((pos_x, pos_y))
        self.velocity = Vector((vel_x, vel_y))

        ttl1, ttl2, self.damage, self.size, = (
            bytes[pos] for pos in (16, 17, 18, 19)
        )
        self.time_to_live = ttl1 << 8 + ttl2

    def to_bytes(self):
        res = bytearray()
        res += pack('f', self.position[0])
        res += pack('f', self.position[1])
        res += pack('f', self.velocity[0])
        res += pack('f', self.velocity[1])
        res += self.time_to_live.to_bytes(2, 'big')
        res += self.damage.to_bytes(1, 'big')
        res += self.size.to_bytes(1, 'big')
        return res


class Player(Entity):
    sin = math.sin(math.radians(TURN_angle))
    cos = math.cos(math.radians(TURN_angle))
    byte_len = 7*4 + 1*4

    def __init__(self, field, name, x=MAX_POSITION // 2, y=MAX_POSITION // 2):
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
            x = random.randint(self.size, MAX_POSITION - self.size)
            y = random.randint(self.size, MAX_POSITION - self.size)
        vector = Vector((limit_zero(x, MAX_POSITION), limit_zero(y, MAX_POSITION)))
        self.position = vector

    def set_velocity(self, x=-1, y=-1):
        if x == -1 and y == -1:
            x = random.randint(-MAX_POSITION, MAX_POSITION)
            y = random.randint(-MAX_POSITION, MAX_POSITION)
        vector = Vector((x, y))
        self.velocity = vector.limit(MAX_VELOCITY)

    def move(self):
        self.position += self.velocity
        self.position.limit_zero(MAX_POSITION)
        self.velocity *= FRICTION

    def steer(self, turn, forward, shoot=0):
        if turn < 0:  # clockwise
            rotation_matrix = Matrix(((Player.cos, Player.sin), (-Player.sin, Player.cos)))
        elif turn > 0:  # anti clockwise
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
        if x_pos + size > MAX_POSITION:
            self.velocity += Vector((MAX_POSITION - (x_pos + size), 0)) * spring_factor
            #self.direction *= Vector((-1, 1))
            bounce = True
        elif x_pos - size < 0:
            self.velocity += Vector((-x_pos + size, 0)) * spring_factor
            #self.direction *= Vector((-1, 1))
            bounce = True

        if y_pos + size > MAX_POSITION:
            self.velocity += Vector((0, MAX_POSITION - (y_pos + size))) * spring_factor
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
        recoil = 3
        cool_down = 100
        if self.cool_down:
            return
        self.cool_down = cool_down
        self.velocity += self.direction * -recoil
        self.field.new_projectile(Projectile(self.position + self.direction*self.size, self.direction*5, 1))

    def is_hit(self, projectile):
        if (self.position-projectile.position).length_squared < self.size ** 2:
            self.velocity += projectile.velocity
            self.damage += 1
            projectile.time_to_live = 0
            return True
        else:
            return False

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

        target_id, self.damage, self.points, self.cool_down = (
            bytes[pos] for pos in (28, 29, 30, 31)
        )
        self.target = field.players[target_id]

    def to_bytes(self):
        # current length  7*4 + 1*4 = 32 bytes
        res = bytearray()
        res += pack('f', self.position[0])  # 4
        res += pack('f', self.position[1])  # 4
        res += pack('f', self.direction[0])  # 4
        res += pack('f', self.direction[1])  # 4
        res += pack('f', self.velocity[0])  # 4
        res += pack('f', self.velocity[1])  # 4
        res += pack('f', self.acceleration)  # 4
        res += self.target.name.to_bytes(1, 'big')  # 1
        res += self.damage.to_bytes(1, 'big')  # 1
        res += self.points.to_bytes(1, 'big')  # 1
        res += self.cool_down.to_bytes(1, 'big')  # 1
        return res
