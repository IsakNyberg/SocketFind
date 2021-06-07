import math

import pygame

from field import *


DISPLAY_ID = 1

BACKGROUND = '#000000'
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'
PROJECTILE_COLOUR = '#e0303a'
BG = pygame.image.load("resources/bg2.jpg")
MINI_OFFSET = 100


def draw_world(screen, offset_x=0, offset_y=0):
    screen.fill(BACKGROUND)
    screen.blit(BG, (-offset_x, -offset_y))


def draw_entity(screen, entity, colour=OTHER_COLOUR, offset_x=0, offset_y=0, mini=False):
    mult = 0.1 if mini else 1
    colour = colour._value

    x = (entity.position[0] - offset_x) * mult
    y = (entity.position[1] - offset_y) * mult
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


def draw_projectile(screen, projectile, x_offset=0, y_offset=0):
    colour = PROJECTILE_COLOUR
    offset = Vector((x_offset, y_offset))

    p_x = projectile.position[0]
    p_y = projectile.position[1]
    if abs(p_x - x_offset) > 800:
        return  # yes Grisha i know that the else is no needed but i think it adds clarity
    if abs(p_y - y_offset) > 800:
        return
    else:
        start = (projectile.position + projectile.velocity*5 - offset)
        end = (projectile.position - projectile.velocity*5 - offset)
        pygame.draw.line(screen, colour, start.to_tuple(), end.to_tuple())
