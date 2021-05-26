import pygame
import math
from field import *

DISPLAY_ID = 1

BACKGROUND = '#000000'
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'
BG = pygame.image.load("resources/bg2.jpg")
MINI_OFFSET = 100


def draw_world(screen, offset_x=0, offset_y=0):
    screen.fill(BACKGROUND)
    screen.blit(BG, (-offset_x, -offset_y))


def draw_entity(screen, entity, colour=OTHER_COLOUR, offset_x=0, offset_y=0, mini=False):
    mult = 0.1 if mini else 1
    colour = colour.to_list()

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



