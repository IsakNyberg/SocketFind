import math
import random
from random import randint as r

import pygame

from field import *
from constants import *

from matrixx import Vector as V

DISPLAY_ID = 1

BACKGROUND = '#000000'
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'
# PROJECTILE_COLOUR = '#e0303a' use projectile.colour instead
BG = pygame.image.load("resources/bg2.jpg")
MINI_OFFSET = 100

total_stars = 500
parallax = 0.5
star_min, star_max = int(-SCREEN_SIZE * parallax), int(FIELD_SIZE * parallax + SCREEN_SIZE)
stars = tuple(Vector((r(star_min, star_max), r(star_min, star_max))) for _ in range(total_stars))
parallax_list = tuple(random.random() / 5 + 0.3 for _ in range(total_stars))


def draw_world(screen, field, player):
    screen.fill(BACKGROUND)
    pos = player.position - V((HALF_SCREEN, HALF_SCREEN))
    for start, end in field.walls:
        start_perspective = start - pos
        end_perspective = end - pos
        pygame.draw.line(
            screen,
            '#a40000',
            start_perspective.to_tuple(),
            end_perspective.to_tuple(),
            5,
        )
    for star, parallax in zip(stars, parallax_list):
        parallax_pos = pos * parallax
        # your stuff didn't work :_(
        if abs(star[0] - parallax_pos[0]) > SCREEN_SIZE:
            continue
        elif abs(star[1] - parallax_pos[1]) > SCREEN_SIZE:
            continue
        pygame.draw.circle(
            screen,
            '#ccccff',
            (star - parallax_pos).to_tuple(),
            1 if r(0, 200) else 2,
        )


def draw_player(screen, entity, colour=V([0x6c, 0x55, 0xe0]), offset=V((0, 0)), mini=False):
    # todo adapt this with vectors
    mult = 0.1 if mini else 1
    colour = colour.to_tuple()

    screen_pos = V((HALF_SCREEN, HALF_SCREEN))
    x = (entity.position[0] - offset[0] + screen_pos[0]) * mult
    y = (entity.position[1] - offset[1] + screen_pos[1]) * mult
    size = entity.size * mult

    front_x = x + size * entity.direction[0] * 1.5
    front_y = y + size * entity.direction[1] * 1.5
    o_x, o_y = entity.direction[1] * size * 0.4, entity.direction[0] * size * 0.4

    if mini:
        pygame.draw.polygon(screen, colour, [
            (x - o_x, y + o_y + MINI_OFFSET),
            (x + o_x, y - o_y + MINI_OFFSET),
            (front_x, front_y + MINI_OFFSET),
        ])
        pygame.draw.circle(screen, colour, (x, y + MINI_OFFSET), size)
    else:
        pygame.draw.polygon(screen, colour, [
            (x - o_x, y + o_y),
            (x + o_x, y - o_y),
            (front_x, front_y),
        ])
        pygame.draw.circle(screen, colour, (x, y), size, width=2)
        pygame.draw.circle(screen, colour, (x, y), size - 10)


def draw_projectile(screen, projectile, offset=V((0, 0))):
    colour = projectile.colour
    screen_center = V((HALF_SCREEN, HALF_SCREEN))

    # todo infnorm this
    if (projectile.position - offset).length_squared > SCREEN_SIZE_SQ:
        return

    if projectile.shape == 1:  # line
        start = (projectile.position - offset + screen_center).to_tuple()
        end = (projectile.position - projectile.velocity*projectile.size - offset + screen_center).to_tuple()
        pygame.draw.line(screen, colour, start, end)
    elif projectile.shape == 2:  # circle
        position = (projectile.position - offset + screen_center).to_tuple()
        radius = projectile.size
        pygame.draw.circle(screen, colour, position, radius)
    else:
        print(f'Projectile shape ({projectile.shape}) unknown.')
