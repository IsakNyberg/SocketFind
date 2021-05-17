import random
from struct import pack, unpack

MAX_ACCELERATION = 1
ACCELERATION_FRACTION = 50
FRICTION = 0.99
MAX_VELOCITY = 2
MAX_POSITION_X = 1440
MAX_POSITION_Y = 850
SIZE = 20


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
        self.size = SIZE
        self.x_position = 0
        self.y_position = 0
        self.x_velocity = 0
        self.y_velocity = 0
        self.x_acceleration = 0
        self.y_acceleration = 0

    @property
    def score(self):
        return self.points - self.damage

    def steer(self, x, y):
        self.x_acceleration = limit(x, MAX_ACCELERATION)
        self.y_acceleration = limit(y, MAX_ACCELERATION)

    def accelerate(self):
        self.x_velocity += self.x_acceleration / ACCELERATION_FRACTION
        self.y_velocity += self.y_acceleration / ACCELERATION_FRACTION

        self.x_velocity = limit(self.x_velocity, MAX_VELOCITY)
        self.y_velocity = limit(self.y_velocity, MAX_VELOCITY)

        self.x_acceleration *= FRICTION
        self.y_acceleration *= FRICTION

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
            return False
        dist_squared = (self.x_position - other.x_position) ** 2 + (self.y_position - other.y_position) ** 2
        if dist_squared < (self.size + other.size) ** 2:
            self.ball_bounce(other)
            if self.weakness == other.name:
                self.damage += 1
                other.points += 1
                other.size -= 1
                self.size += 1
                return True
        return False

    def new_weakness(self, players):
        self.weakness = self.name
        while self.weakness == self.name:
            self.weakness = random.randint(0, players-1)
        return self.weakness

    def wall_bounce(self):
        if self.x_position + self.size > MAX_POSITION_X or self.x_position - self.size < 0:
            self.x_velocity *= -1

        if self.y_position + self.size > MAX_POSITION_Y or self.y_position - self.size < 0:
            self.y_velocity *= -1

    def ball_bounce(self, other):
        x = (self.x_position - other.x_position) * 10
        y = (self.y_position - other.y_position) * 10
        self.x_velocity = limit(x, MAX_VELOCITY * 5)
        self.y_velocity = limit(y, MAX_VELOCITY * 5)


class Field:
    def __init__(self):
        self.entities = []
        self.status = 0

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
        if len(self.entities) >= 3:
            self.new_targets()
        return entity

    def remove(self, name):
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
        for entity in self.entities:
            entity.new_weakness(len(self.entities))

    def steer(self, n, x, y):
        self.mutex_wait()
        self.entities[n].steer(x, y)
        self.mutex = 0

    def tick(self):
        if self.mutex:
            return
        for entity in self.entities:
            entity.accelerate()
            entity.move()
            entity.wall_bounce()

        for entity_a in self.entities:
            for entity_b in self.entities:
                if entity_a.is_colliding(entity_b):
                    entity_a.new_weakness(len(self.entities))

    def from_bytes(self, received_bytes):
        self.mutex_wait()
        s = 4 * 6 + 3
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
            self.entities[i].x_acceleration = unpack('f', received_bytes[i * s + 16: i * s + 20])[0]
            self.entities[i].y_acceleration = unpack('f', received_bytes[i * s + 20: i * s + 24])[0]
            self.entities[i].weakness = received_bytes[i * s + 24]
            self.entities[i].damage = received_bytes[i * s + 25]
            self.entities[i].points = received_bytes[i * s + 26]
        self.mutex = 0

    def to_bytes(self):
        res = bytearray()
        for i in range(len(self.entities)):
            res += pack('f', self.entities[i].x_position)
            res += pack('f', self.entities[i].y_position)
            res += pack('f', self.entities[i].x_velocity)
            res += pack('f', self.entities[i].y_velocity)
            res += pack('f', self.entities[i].x_acceleration)
            res += pack('f', self.entities[i].y_acceleration)
            res += self.entities[i].weakness.to_bytes(1, 'big')
            res += self.entities[i].damage.to_bytes(1, 'big')
            res += self.entities[i].points.to_bytes(1, 'big')

        return res

