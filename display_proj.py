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

LIGHT_MIN = 0.4  # between 0 and 0.5, do NOT put 0.5 or higher here please
LIGHT_HALF_LIFE = 700

# light intensity: f(x) = a/(x^2+b) + c
LIGHT_C = LIGHT_MIN
LIGHT_B = LIGHT_HALF_LIFE**2 * (1 - 2*LIGHT_C)  # maths checks out, I promise
LIGHT_A = LIGHT_B * (1-LIGHT_C)
DARKENER = lambda x: LIGHT_A/(x**2 + LIGHT_B) + LIGHT_C

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
        depth = dist * cos
        col_height = min(screen_size, screen_size * 50 / depth)
        dark = DARKENER(dist)
        col = pygame.Rect(
            i*col_width - 1,  # add overlap
            screen_mid - col_height/2,
            col_width + 2,  # add overlap
            col_height,
        )
        pygame.draw.rect(screen, tuple(map(dark.__mul__, WALL_COLOUR)), col)


def draw_entity(screen, entity, colour=OTHER_COLOUR, **kwargs):
    # "minimap"
    display.draw_entity(screen, entity, colour, **kwargs, mini=True)





