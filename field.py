import random
import math
import time

from entity import *
import weapons

from matrixx import Vector

MIN_PLAYERS = 3
WALL_COLLISION = 1 << 0
OTHER_COLLISION = 1 << 1
SELF_HIT = 1 << 2
TARGET_HIT = 1 << 3
JOIN = 1 << 4


class Field:
    walls = (
        (Vector((0, 0)), Vector((FIELD_SIZE, 0))),
        (Vector((0, 0)), Vector((0, FIELD_SIZE))),
        (Vector((FIELD_SIZE, FIELD_SIZE)), Vector((FIELD_SIZE, 0))),
        (Vector((FIELD_SIZE, FIELD_SIZE)), Vector((0, FIELD_SIZE))),
    )

    def __init__(self):
        self.players = []
        self.projectiles = []
        self.status = []

        self.mutex = 0

        self.self_index = -1
        self.tick_count = 0
        self.next_tick = time.time()

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
        x = random.randint(entity.size, FIELD_SIZE - entity.size)
        y = random.randint(entity.size, FIELD_SIZE - entity.size)
        entity.set_position(x, y)
        self.players.append(entity)
        self.status.append(JOIN)
        if len(self.players) >= MIN_PLAYERS:
            self.new_targets()
        return entity

    def new_projectile(self, projectile):
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
            ((0, 0), (0, FIELD_SIZE)),
            ((0, 0), (FIELD_SIZE, 0)),
            ((FIELD_SIZE, FIELD_SIZE), (0, FIELD_SIZE)),
            ((FIELD_SIZE, FIELD_SIZE), (FIELD_SIZE, 0)),
            ((FIELD_SIZE/2, FIELD_SIZE/2), (FIELD_SIZE/2, 0)),  # del me
            ((FIELD_SIZE/2, FIELD_SIZE/2), (FIELD_SIZE/4, 0)),
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
        return min_t

    def tick(self, self_index=-1):
        # WALL_COLLISION 0, OTHER_COLLISION 1, SELF_HIT 2, TARGET_HIT 3, JOIN 4
        while self.mutex:
            pass
        t = time.time()
        if t < self.next_tick:
            time.sleep(self.next_tick - t)
        self.next_tick = time.time() + 1 / 120

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
                    entity_b.points += 1
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
        self.projectiles = []

        received_bytes = received_bytes[2:]
        for i, player in enumerate(self.players):
            player.from_bytes(received_bytes[i * Player.byte_len: (i+1) * Player.byte_len], self)

        received_bytes = received_bytes[players * Player.byte_len:]
        byte_len = weapons.Weapon.byte_len
        for i in range(projectiles):
            relevant_bytes = received_bytes[i * byte_len: (i+1) * byte_len]
            projectile = weapons.from_bytes(self.players, relevant_bytes)
            self.projectiles.append(projectile)

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
