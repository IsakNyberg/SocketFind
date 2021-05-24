import pygame
import math
import display
from field import MAX_POSITION
from matrix import Matrix as M

DISPLAY_ID = 2

BACKGROUND = '#111111'
WALL_COLOUR = (0x36, 0x36, 0x36)

SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'

FOV = 140
DEG_PER_COL = 1

factory = lambda x: M([[math.cos(x),-math.sin(x)], [math.sin(x),math.cos(x)]])
directions = map(math.radians, range(-FOV//2, 1+FOV//2, DEG_PER_COL))
rot_mats = list(map(factory, directions))


def draw_world(screen, field, player, screen_size):
    screen.fill(BACKGROUND)
    pos, view = player.position, player.direction
    col_width = screen_size/len(rot_mats)
    screen_mid = screen_size//2
    dark_mult = 0.6/MAX_POSITION

    for i, rot_mat in enumerate(rot_mats):
        ray = rot_mat @ view
        dist = field.cast_ray_at_wall(pos, ray)
        col_height = screen_size
        if dist > 50:
            col_height = min(screen_size, screen_size*50//dist)
        dark = 1 - dist*dark_mult
        col = pygame.Rect(
            i*col_width,
            screen_mid-col_height//2,
            col_width,
            col_height,
        )
        pygame.draw.rect(screen, tuple(map(dark.__mul__, WALL_COLOUR)), col)


def draw_entity(screen, entity, colour=OTHER_COLOUR, **kwargs):
    # "minimap"
    display.draw_entity(screen, entity, colour, **kwargs, mini=True)





