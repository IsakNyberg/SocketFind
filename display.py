import pygame
import math
from field import *

BACKGROUND = '#363638'
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'


def draw_entity(screen, entity, colour=OTHER_COLOUR, offset_x=0, offset_y=0):
    x = entity.position[0] - offset_x
    y = entity.position[1] - offset_y
    size = entity.size

    front_x = x + size * entity.direction[0] * 1.5
    front_y = y + size * entity.direction[1] * 1.5
    o_x, o_y = entity.direction[1] * size * 0.4, entity.direction[0] * size * 0.4
    pygame.draw.polygon(screen, colour, [
        (x - o_x, y + o_y),
        (x + o_x, y - o_y),
        (front_x, front_y),
    ])

    pygame.draw.circle(screen, colour, (x, y), entity.size, width=4)
    pygame.draw.circle(screen, colour, (x, y), entity.size//2)


