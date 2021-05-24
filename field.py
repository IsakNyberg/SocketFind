import random
from struct import pack, unpack
import math
from operator import not_

from matrix import Vector, Matrix

MAX_ACCELERATION = 1
ACCELERATION_FRACTION = 30
TURN_angle = 2  # 120 * this many degrees per second
FRICTION = 0.99
MAX_VELOCITY = 4
MAX_POSITION = 2000
SIZE = 20
GRAVITY_FRACTION = 70

MIN_PLAYERS = 3

WALL_COLLISION = 1 << 0
OTHER_COLLISION = 1 << 1
WEAKNESS_COLLISION = 1 << 2
POINT_COLLISION = 1 << 3
JOIN = 1 << 4


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
    def __init__(self, name, x=MAX_POSITION // 2, y=MAX_POSITION // 2):
        self.name = name
        self.position = Vector([x, y])
        self.velocity = Vector([0, 0])
        self.direction = Vector([0.0, 0.0])
        self._size = SIZE

    @property
    def size(self):
        return self._size

    def set_position(self, x=-1, y=-1):
        if x == -1 and y == -1:
            x = random.randint(self.size, MAX_POSITION - self.size)
            y = random.randint(self.size, MAX_POSITION - self.size)
        vector = Vector([limit_zero(x, MAX_POSITION), limit_zero(y, MAX_POSITION)])
        self.position = vector

    def set_velocity(self, x=-1, y=-1):
        if x == -1 and y == -1:
            x = random.randint(-MAX_POSITION, MAX_POSITION)
            y = random.randint(-MAX_POSITION, MAX_POSITION)
        vector = Vector([x, y])
        self.velocity = vector.limit(MAX_VELOCITY)

    def wall_bounce(self):
        bounce = False
        if self.position[0] + self.size > MAX_POSITION:
            self.velocity[0] = -MAX_VELOCITY
            self.direction[0] *= -1
            bounce = True
        elif self.position[0] - self.size < 0:
            self.velocity[0] = MAX_VELOCITY
            self.direction[0] *= -1
            bounce = True

        if self.position[1] + self.size > MAX_POSITION:
            self.velocity[1] = -MAX_VELOCITY
            self.direction[1] *= -1
            bounce = True
        elif self.position[1] - self.size < 0:
            self.velocity[1] = MAX_VELOCITY
            self.direction[1] *= -1
            bounce = True
        return bounce

    def gravity(self, mass):
        acceleration = mass.position - self.position
        if acceleration.length_squared == 0:
            return
        dist_factor = (acceleration.length // GRAVITY_FRACTION ** 2) ** 2
        self.velocity += acceleration.unit * (1 / (GRAVITY_FRACTION + dist_factor))
        self.velocity.limit(MAX_VELOCITY)

    def move(self):
        self.position += self.velocity
        self.position.limit_zero(MAX_POSITION)
        self.velocity *= FRICTION


class Player(Entity):
    sin = math.sin(math.radians(TURN_angle))
    cos = math.cos(math.radians(TURN_angle))

    def __init__(self, name):
        super().__init__(name)
        self.target = self
        self.self_index = -1
        self.damage = 0
        self.points = 0
        self.acceleration = 0
        self.direction = Vector([1.0, 0.0])
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

    def steer(self, turn, forward):
        if turn < 0:  # clockwise
            rotation_matrix = Matrix([[Player.cos, Player.sin], [-Player.sin, Player.cos]])
        elif turn > 0:  # anti clockwise
            rotation_matrix = Matrix([[Player.cos, -Player.sin], [Player.sin, Player.cos]])
        else:
            rotation_matrix = None

        if rotation_matrix is not None:
            self.direction = rotation_matrix @ self.direction
            self.direction = self.direction.unit

        if forward < 0:
            self.velocity *= FRICTION ** 6
        elif forward > 0:
            self.acceleration = 1
        else:
            self.acceleration = 0

    def accelerate(self):
        if self.acceleration == 0:
            return
        acceleration = self.direction * (self.acceleration / ACCELERATION_FRACTION)
        self.velocity += acceleration
        self.velocity.limit(MAX_VELOCITY)
        self.acceleration *= FRICTION

    def is_colliding(self, other):
        if other is self:
            return 0
        dist_squared = (self.position - other.position).length_squared
        if dist_squared < (self.size + other.size) ** 2:
            self.ball_bounce(other)
            if self.target is other and not self.cool_down:
                self.points += 1
                other.damage += 1
                self.cool_down = 255
                other.cool_down = 255
                return 2
            return 1
        return 0

    def new_target(self, players):
        self.target = self
        if len(players) < MIN_PLAYERS:
            return self

        """if all(player.target == self for player in players):
            self.target = players[random.randint(0, len(players) - 1)]"""
        tries = 0
        while self.target == self or (self.target.target is self and tries < len(players) * 2):
            self.target = players[random.randint(0, len(players)-1)]
        return self.target

    def ball_bounce(self, other):
        try:
            new_velocity = (self.position - other.position).unit
            new_length = (self.velocity.length + other.velocity.length) / 2
            self.velocity = new_velocity * new_length
            other.velocity = new_velocity * -new_length
        except ZeroDivisionError:
            pass


class Field:
    def __init__(self):
        self.players = []
        self.status = []

        self.mutex = 0

        self.self_index = -1

    @property
    def score(self):
        best = 0
        for entity in self.players:
            if entity.points > best:
                best = entity.points
        return best

    @property
    def entities(self):
        return self.players

    def mutex_wait(self):
        while self.mutex:
            pass
        self.mutex = 1

    def append(self, entity):
        self.players.append(entity)

    def new_player(self):
        entity = Player(len(self.players))
        x = random.randint(entity.size, MAX_POSITION - entity.size)
        y = random.randint(entity.size, MAX_POSITION - entity.size)
        entity.set_position(x, y)
        self.players.append(entity)
        self.status.append(JOIN)
        if len(self.players) == MIN_PLAYERS:
            self.new_targets()
        print('join', len(self.players))

    def remove(self, index):
        self.status.append(JOIN)
        del self.players[index]
        for i in range(len(self.players)):
            self.players[i].name = i
        self.new_targets()
        print('leave', len(self.players))

    def new_targets(self):
        self.status.append(POINT_COLLISION)
        for entity in self.players:
            entity.new_target(self.players)

    def steer(self, n, x, y):
        self.mutex_wait()
        self.players[n].steer(x, y)
        self.mutex = 0

    def cast_ray_at_wall(self, pos, step):
        """Distance to first wall from pos in direction step."""
        walls = (
            ((0, 0), (0, MAX_POSITION)),
            ((0, 0), (MAX_POSITION, 0)),
            ((MAX_POSITION, MAX_POSITION), (0, MAX_POSITION)),
            ((MAX_POSITION, MAX_POSITION), (MAX_POSITION, 0)),
            ((MAX_POSITION/2, MAX_POSITION/2), (MAX_POSITION/2, 0)),  # del me
        )
        x1, y1 = pos
        x2, y2 = pos + step
        min_t = inf = float('inf')
        for ((x3, y3), (x4, y4)) in walls:
            Np = (x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)
            Nw = (x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)
            D  = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if (
                D  # D is non-zero
                and (0 < D) == (0 < Np)
                # t=Np/D is positive (wall ahead of player)
                and min(0, D) < Nw < max(0, D)
                # 0 < u=Nw/D < length (intersection within wall bounds)
                and (t := Np/D) < min_t
                # this wall is close than the last
            ):
                min_t = t
        assert min_t < inf, "Not facing any wall"
        return min_t

    def tick(self, self_index=-1):
        # WALL_COLLISION 0, OTHER_COLLISION 1, WEAKNESS_COLLISION 2, POINT_COLLISION 3, JOIN 4
        if self.mutex:
            return []

        for player in self.players:
            player.accelerate()
            player.move()
            if player.cool_down:
                player.cool_down -= 1

            if player.wall_bounce():
                self.status.append(WALL_COLLISION)

        for entity_a in self.players:
            for entity_b in self.players:
                if entity_a is entity_b:
                    continue
                collision = entity_a.is_colliding(entity_b)
                if collision == 1:
                    self.status.append(OTHER_COLLISION)
                elif collision == 2:
                    entity_a.new_target(self.players)
                    if self_index == entity_a.name:
                        self.status.append(WEAKNESS_COLLISION)
                    elif self_index == entity_b.name:
                        self.status.append(POINT_COLLISION)

        status = self.status
        self.status = []
        return status

    def from_bytes(self, received_bytes):
        self.mutex_wait()
        s = 4 * 7 + 4
        players = len(received_bytes) // s
        while players < len(self.players):
            self.remove(-1)
        while players > len(self.players):
            self.new_player()

        for i in range(players):
            self.players[i].position[0] = unpack('f', received_bytes[i * s + 0: i * s + 4])[0]
            self.players[i].position[1] = unpack('f', received_bytes[i * s + 4: i * s + 8])[0]
            self.players[i].direction[0] = unpack('f', received_bytes[i * s + 8: i * s + 12])[0]
            self.players[i].direction[1] = unpack('f', received_bytes[i * s + 12: i * s + 16])[0]
            self.players[i].velocity[0] = unpack('f', received_bytes[i * s + 16: i * s + 20])[0]
            self.players[i].velocity[1] = unpack('f', received_bytes[i * s + 20: i * s + 24])[0]
            self.players[i].acceleration = unpack('f', received_bytes[i * s + 24: i * s + 28])[0]
            self.players[i].target = self.players[received_bytes[i * s + 28]]
            self.players[i].damage = received_bytes[i * s + 29]
            self.players[i].points = received_bytes[i * s + 30]
            self.players[i].cool_down = received_bytes[i * s + 31]
        self.mutex = 0

    def to_bytes(self):
        res = bytearray()
        for i in range(len(self.players)):
            res += pack('f', self.players[i].position[0])
            res += pack('f', self.players[i].position[1])
            res += pack('f', self.players[i].direction[0])
            res += pack('f', self.players[i].direction[1])
            res += pack('f', self.players[i].velocity[0])
            res += pack('f', self.players[i].velocity[1])
            res += pack('f', self.players[i].acceleration)
            res += self.players[i].target.name.to_bytes(1, 'big')
            res += self.players[i].damage.to_bytes(1, 'big')
            res += self.players[i].points.to_bytes(1, 'big')
            res += self.players[i].cool_down.to_bytes(1, 'big')

        return res
