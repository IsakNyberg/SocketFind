import random
import math
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

MIN_PLAYERS = 3

WALL_COLLISION = 1 << 0
OTHER_COLLISION = 1 << 1
SELF_HIT = 1 << 2
TARGET_HIT = 1 << 3
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


class Projectile:
    byte_len = 4*4 + 1*4

    def __init__(self, position, velocity, damage=1, range=1024):
        self.position = position
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


class Player:
    sin = math.sin(math.radians(TURN_angle))
    cos = math.cos(math.radians(TURN_angle))
    byte_len = 7*4 + 1*4

    def __init__(self, field, name, x=MAX_POSITION // 2, y=MAX_POSITION // 2):
        self.field = field
        self.name = name
        self.position = Vector((x, y))
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

    def get_dist_squared(self, pos):
        return (self.position - pos).length_squared

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
        if len(players) < MIN_PLAYERS:
            return self

        tries = 0 if MIN_PLAYERS < len(players) else len(players)
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
        recoil = 4
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


class Field:
    walls = (
        (Vector((0, 0)), Vector((MAX_POSITION, 0))),
        (Vector((0, 0)), Vector((0, MAX_POSITION))),
        (Vector((MAX_POSITION, MAX_POSITION)), Vector((MAX_POSITION, 0))),
        (Vector((MAX_POSITION, MAX_POSITION)), Vector((0, MAX_POSITION))),
    )

    def __init__(self):
        self.players = []
        self.projectiles = []
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

    def get_players_by_dist(self, pos):
        return self.players.sort(key=lambda x: x.get_dist_squared(pos), reverse=True)

    def mutex_wait(self):
        while self.mutex:
            pass
        self.mutex = 1

    def append(self, entity):
        self.players.append(entity)

    def new_player(self):
        entity = Player(self, len(self.players))
        x = random.randint(entity.size, MAX_POSITION - entity.size)
        y = random.randint(entity.size, MAX_POSITION - entity.size)
        entity.set_position(x, y)
        self.players.append(entity)
        self.status.append(JOIN)
        if len(self.players) >= MIN_PLAYERS:
            self.new_targets()
        return entity

    def new_projectile(self, projectile=None):
        if projectile is None:
            self.projectiles.append(Projectile(Vector((0,0)), Vector((0,0))))
        else:
            self.projectiles.append(projectile)

    def remove(self, index):
        self.status.append(JOIN)
        del self.players[index]
        for i in range(len(self.players)):
            self.players[i].name = i
        self.new_targets()

    def new_targets(self):
        self.status.append(TARGET_HIT)
        for entity in self.players:
            entity.new_target(self.players)

    def steer(self, n, turn, forward, shoot):
        self.mutex_wait()
        self.players[n].steer(turn, forward, shoot)
        self.mutex = 0

    def cast_ray_at_wall(self, pos, step):
        """Distance to first wall from pos in direction step."""
        walls = (
            ((0, 0), (0, MAX_POSITION)),
            ((0, 0), (MAX_POSITION, 0)),
            ((MAX_POSITION, MAX_POSITION), (0, MAX_POSITION)),
            ((MAX_POSITION, MAX_POSITION), (MAX_POSITION, 0)),
            ((MAX_POSITION/2, MAX_POSITION/2), (MAX_POSITION/2, 0)),  # del me
            ((MAX_POSITION/2, MAX_POSITION/2), (MAX_POSITION/4, 0)),
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
        # WALL_COLLISION 0, OTHER_COLLISION 1, SELF_HIT 2, TARGET_HIT 3, JOIN 4
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
            hit_players = []
            for projectile in self.projectiles:
                if entity_a.is_hit(projectile):
                    hit_players.append(entity_a)
                    if self_index == entity_a.name:
                        self.status.append(SELF_HIT)
                    elif self_index == entity_a.name:
                        self.status.append(TARGET_HIT)

            for entity_b in self.players:
                if entity_b.target in hit_players:
                    entity_b.new_target(self.players)
                if entity_a is entity_b:
                    continue
                if entity_a.is_colliding(entity_b):
                    self.status.append(OTHER_COLLISION)

        for projectile in self.projectiles:
            if projectile.tick():
                self.projectiles.remove(projectile)
        status = self.status
        self.status = []
        return status

    def from_bytes(self, received_bytes):
        self.mutex_wait()
        players = received_bytes[0]
        while players < len(self.players):
            self.remove(-1)
        while players > len(self.players):
            self.new_player()

        projectiles = received_bytes[1]
        while projectiles < len(self.projectiles):
            del self.projectiles[0]
        while projectiles > len(self.projectiles):
            self.new_projectile()

        received_bytes = received_bytes[2:]
        for i, player in enumerate(self.players):
            player.from_bytes(received_bytes[i * Player.byte_len: (i+1) * Player.byte_len], self)

        received_bytes = received_bytes[players * Player.byte_len:]
        for i, projectile in enumerate(self.projectiles):
            projectile.from_bytes(received_bytes[i * Projectile.byte_len: (i+1) * Projectile.byte_len])

        self.mutex = 0

    def to_bytes(self):
        res = bytearray()
        res += len(self.players).to_bytes(1, 'big')
        res += len(self.projectiles).to_bytes(1, 'big')
        for player in self.players:
            res += player.to_bytes()
        for projectile in self.projectiles:
            res += projectile.to_bytes()

        return res
