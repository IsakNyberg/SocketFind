import random
from struct import pack, unpack
import math

MAX_ACCELERATION = 1
ACCELERATION_FRACTION = 30
TURN_angle = 2  # 120 * this many degrees per second
FRICTION = 0.99
MAX_VELOCITY = 4
MAX_POSITION_X = 1440
MAX_POSITION_Y = 850
SIZE = 20

WALL_COLLISION = 1 << 0
OTHER_COLLISION = 1 << 1
WEAKNESS_COLLISION = 1 << 2
POINT_COLLISION = 1 << 3
JOIN = 1 << 4


def normalize(a, b):
    sum_ = math.sqrt(a*a + b*b)
    if sum_ == 0:
        return 0, 0
    return limit(a/sum_, 1), limit(b/sum_, 1)


def limit(n, lim):
    return max(min(lim, n), -lim)


def limit_zero(n, lim):
    return max(min(lim, n), 0)


class Entity:
    def __init__(self, name, weakness=255):
        self.name = name
        self.weakness = weakness
        self.self_index = -1
        self.damage = 0
        self.points = 0
        #self.size = SIZE
        self.x_position = 0
        self.y_position = 0
        self.x_velocity = 0
        self.y_velocity = 0
        self.acceleration = 0
        self.direction = [1, 0]

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
        turn_a = math.sin(math.radians(TURN_angle * turn))
        turn_b = math.cos(math.radians(TURN_angle * turn))
        self.direction = [
            self.direction[0] * turn_b - self.direction[1] * turn_a,
            self.direction[0] * turn_a + self.direction[1] * turn_b,
        ]
        self.direction[0], self.direction[1] = normalize(self.direction[0], self.direction[1])
        if forward < 0:
            self.y_velocity *= FRICTION ** 5
            self.x_velocity *= FRICTION ** 4
        elif forward > 0:
            self.acceleration = 1
        else:
            self.acceleration = 0

    def accelerate(self):
        if self.acceleration == 0:
            return
        x_acceleration = self.direction[0] * self.acceleration
        y_acceleration = self.direction[1] * self.acceleration
        self.x_velocity += x_acceleration / ACCELERATION_FRACTION
        self.y_velocity += y_acceleration / ACCELERATION_FRACTION
        self.x_velocity = limit(self.x_velocity, MAX_VELOCITY)
        self.y_velocity = limit(self.y_velocity, MAX_VELOCITY)
        self.acceleration *= FRICTION

    def move(self):
        self.x_position += self.x_velocity
        self.y_position += self.y_velocity

        self.x_position = limit_zero(self.x_position, MAX_POSITION_X)
        self.y_position = limit_zero(self.y_position, MAX_POSITION_Y)

        self.x_velocity *= FRICTION
        self.y_velocity *= FRICTION

    def set_position(self, x, y):
        self.x_position = limit_zero(x, MAX_POSITION_X)
        self.y_position = limit_zero(y, MAX_POSITION_Y)

    def is_colliding(self, other):
        if other is self:
            return 0
        dist_squared = (self.x_position - other.x_position) ** 2 + (self.y_position - other.y_position) ** 2
        if dist_squared < (self.size + other.size) ** 2:
            self.ball_bounce(other)
            if self.weakness == other.name:
                self.damage += 1
                other.points += 1
                return 2
            return 1
        return 0

    def new_weakness(self, players):
        self.weakness = self.name
        while self.weakness == self.name:
            self.weakness = random.randint(0, players-1)
        return self.weakness

    def wall_bounce(self):
        bounce = False
        if self.x_position + self.size > MAX_POSITION_X:
            self.x_velocity = -MAX_VELOCITY
            self.direction[0] = -1
            bounce = True
        elif self.x_position - self.size < 0:
            self.direction[0] = 1
            self.x_velocity = MAX_VELOCITY
            bounce = True

        if self.y_position + self.size > MAX_POSITION_Y:
            self.y_velocity = -MAX_VELOCITY
            self.direction[1] = -1
            bounce = True
        elif self.y_position - self.size < 0:
            self.y_velocity = MAX_VELOCITY
            self.direction[1] = 1
            bounce = True
        return bounce

    def ball_bounce(self, other):
        x = (self.x_position - other.x_position) * abs(self.x_velocity + other.x_velocity) // self.size
        y = (self.y_position - other.y_position) * abs(self.y_velocity + other.y_velocity) // self.size
        self.x_velocity = limit(x, MAX_VELOCITY)
        self.y_velocity = limit(y, MAX_VELOCITY)


class Field:
    def __init__(self):
        self.entities = []
        self.status = []

        self.mutex = 0

    @property
    def score(self):
        best = 0
        for entity in self.entities:
            if entity.points > best:
                best = entity.points
        return best

    def mutex_wait(self):
        while self.mutex:
            pass
        self.mutex = 1

    def append(self, entity):
        self.entities.append(entity)

    def new_player(self):
        entity = Entity(len(self.entities))
        x = random.randint(entity.size, MAX_POSITION_X-entity.size)
        y = random.randint(entity.size, MAX_POSITION_Y-entity.size)
        entity.set_position(x, y)
        self.entities.append(entity)
        self.status.append(JOIN)
        if len(self.entities) >= 3:
            self.new_targets()
        return entity

    def remove(self, name):
        self.status.append(JOIN)
        if name == -1:
            del self.entities[-1]
            return True

        for entity in self.entities:
            if entity.name == name:
                self.entities.remove(entity)
                self.new_targets()
                return True
        return False

    def new_targets(self):
        self.status.append(POINT_COLLISION)
        for entity in self.entities:
            entity.new_weakness(len(self.entities))

    def steer(self, n, x, y):
        self.mutex_wait()
        self.entities[n].steer(x, y)
        self.mutex = 0

    def tick(self, self_index=-1):
        # WALL_COLLISION 0, OTHER_COLLISION 1, WEAKNESS_COLLISION 2, POINT_COLLISION 3, JOIN 4
        if self.mutex:
            return []
        for entity in self.entities:
            entity.accelerate()
            entity.move()
            if entity.wall_bounce():
                self.status.append(WALL_COLLISION)

        for entity_a in self.entities:
            for entity_b in self.entities:
                collision = entity_a.is_colliding(entity_b)
                if collision == 1:
                    self.status.append(OTHER_COLLISION)
                elif collision == 2:
                    entity_a.new_weakness(len(self.entities))
                    if self_index == entity_a.name:
                        self.status.append(WEAKNESS_COLLISION)
                    elif self_index == entity_b.name:
                        self.status.append(POINT_COLLISION)

        status = self.status
        self.status = []
        return status

    def from_bytes(self, received_bytes):
        self.mutex_wait()
        s = 4 * 7 + 3
        players = len(received_bytes) // s
        while players < len(self.entities):
            self.remove(-1)
        while players > len(self.entities):
            self.new_player()

        for i in range(players):
            self.entities[i].x_position = unpack('f', received_bytes[i * s + 0: i * s + 4])[0]
            self.entities[i].y_position = unpack('f', received_bytes[i * s + 4: i * s + 8])[0]
            self.entities[i].x_velocity = unpack('f', received_bytes[i * s + 8: i * s + 12])[0]
            self.entities[i].y_velocity = unpack('f', received_bytes[i * s + 12: i * s + 16])[0]
            self.entities[i].acceleration = unpack('f', received_bytes[i * s + 16: i * s + 20])[0]
            self.entities[i].direction[0] = unpack('f', received_bytes[i * s + 20: i * s + 24])[0]
            self.entities[i].direction[1] = unpack('f', received_bytes[i * s + 24: i * s + 28])[0]
            self.entities[i].weakness = received_bytes[i * s + 28]
            self.entities[i].damage = received_bytes[i * s + 29]
            self.entities[i].points = received_bytes[i * s + 30]
        self.mutex = 0

    def to_bytes(self):
        res = bytearray()
        for i in range(len(self.entities)):
            res += pack('f', self.entities[i].x_position)
            res += pack('f', self.entities[i].y_position)
            res += pack('f', self.entities[i].x_velocity)
            res += pack('f', self.entities[i].y_velocity)
            res += pack('f', self.entities[i].acceleration)
            res += pack('f', self.entities[i].direction[0])
            res += pack('f', self.entities[i].direction[1])
            res += self.entities[i].weakness.to_bytes(1, 'big')
            res += self.entities[i].damage.to_bytes(1, 'big')
            res += self.entities[i].points.to_bytes(1, 'big')

        return res

