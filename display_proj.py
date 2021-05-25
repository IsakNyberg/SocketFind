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

FOV = 100
DEG_PER_COL = 1

factory = lambda x: M([[math.cos(x), -math.sin(x)], [math.sin(x), math.cos(x)]])
phis = tuple(map(math.radians, range(-FOV//2, 1+FOV//2, DEG_PER_COL)))
coss = tuple(map(math.cos, phis))
rot_mats = tuple(map(factory, phis))


def draw_world(screen, field, player, screen_size):
    screen.fill(BACKGROUND)
    pos, view = player.position, player.direction
    col_width = screen_size/len(rot_mats)
    screen_mid = screen_size//2
    dark_mult = 0.6/MAX_POSITION

    for i, (cos, rot_mat) in enumerate(zip(coss, rot_mats)):
        ray = rot_mat @ view
        dist = field.cast_ray_at_wall(pos, ray)
        col_height = screen_size
        if dist > 50:
            col_height = screen_size*50 / (dist*cos)
            col_height = min(screen_size, col_height)
        dark = 1 - dist*dark_mult
        col = pygame.Rect(
            i*col_width,
            screen_mid - col_height/2,
            col_width,
            col_height,
        )
        pygame.draw.rect(screen, tuple(map(dark.__mul__, WALL_COLOUR)), col)


def draw_entity(screen, entity, colour=OTHER_COLOUR, **kwargs):
    # "minimap"
    display.draw_entity(screen, entity, colour, **kwargs, mini=True)





