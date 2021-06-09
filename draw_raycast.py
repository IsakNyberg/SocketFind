import math
import time
from statistics import mean
from multiprocessing import Pool, get_context
from itertools import starmap, cycle

import pygame
from matrixx import Matrix as M, Vector as V, M2

from constants import FIELD_SIZE


_t = time.time()
DISPLAY_ID = 2

# Options
SCREEN_SIZE = 800
FOV_D = 90  # deg
V_FOV_D = 90 # deg
COLUMN_COUNT = 100
ROW_COUNT = 50  # floor only
FLOOR_CHECKERBOARD_SIZE = 20
FLOOR_STYLE = 'checkerboard'  # change this string
CROSSHAIR_SIZE = 15
CROSSHAIR_COLOUR = '#babdb6'


# Floor style stuff
BACKGROUND = V((0x36, 0x36, 0x36)) * 0.2
WALL_COLOUR = V((0x36, 0x36, 0x36))
WALL_COLOURS = [
    V((0x7d, 0xd7, 0xff)),
    V((0xa6, 0xe4, 0xff)),
    V((0x82, 0xd9, 0xff)),
    V((0x5d, 0xcc, 0xfc)),
    V((0x5d, 0xcc, 0xff)),
    V((0x5d, 0xdc, 0xff)),
    V((0x5a, 0xcc, 0xfc)),
    V((0x40, 0xcc, 0xff)),
    V((0x4d, 0xcc, 0xfc)),
]
DARK_TILE = V((0x20, 0x3c, 0x1e))
LITE_TILE = DARK_TILE * 1.2
IMAGE = pygame.image.load("resources/bg2.jpg")
_FLOOR_CHECKERBOARD_COLOURS = (DARK_TILE, LITE_TILE)
_FLOOR_COLOUR = {
    'checkerboard': lambda x, y: _FLOOR_CHECKERBOARD_COLOURS[
        int(x//FLOOR_CHECKERBOARD_SIZE + y//FLOOR_CHECKERBOARD_SIZE) % 2
    ]._value,
    'image': lambda x, y: IMAGE.get_at((int(x), int(y))),
    'plain': lambda x, y: DARK_TILE._value,
}[FLOOR_STYLE]


# light
LIGHT_MIN = 0.4 #0.4  # between 0 and 0.5, do NOT put 0.5 or higher here please
LIGHT_HALF_LIFE = 400  #700
_LIGHT_C = LIGHT_MIN  # light intensity: f(x) = a/(x^2+b) + c
_LIGHT_B = LIGHT_HALF_LIFE**2 * (1 - 2*_LIGHT_C)  # maths checks out, I promise
_LIGHT_A = _LIGHT_B * (1 - _LIGHT_C)
_DARKENER = lambda x: _LIGHT_A / (x**2 + _LIGHT_B) + _LIGHT_C


# General data
_SCREEN_MID = SCREEN_SIZE // 2
_FOV_R = math.radians(FOV_D)
_V_FOV_R = math.radians(V_FOV_D)
_COLUMN_WIDTH = SCREEN_SIZE / COLUMN_COUNT
_COLUMN_WIDTH_DRAW = int(SCREEN_SIZE / COLUMN_COUNT) + 1
_COLUMN_BOUNDARIES = tuple(_COLUMN_WIDTH * i for i in range(COLUMN_COUNT + 1))
    # screen x-coordinates of column boundaries
_ROW_HEIGHT = _SCREEN_MID / ROW_COUNT
_ROW_HEIGHT_DRAW = int(_ROW_HEIGHT) + 1
_ROW_BOUNDARIES = tuple(
    SCREEN_SIZE - i*_ROW_HEIGHT for i in range(ROW_COUNT + 1)
)   # screen y-coordinates of row boundaries
_FIELD_MID = V((_SCREEN_MID, _SCREEN_MID))


# Wall maths:
# Inputs: screen size (SS), FOV
# 1) Calculate distance between camera and view plane:
#       view_dist = SS/2 / tan(FOV/2)
# 2) Calculate horizontal angle for each x of column of equal width on screen
#       theta = atan( (x - (SS/2)) / view_dist )
# 3) Calculate rotation matrix R for each angle theta
# 4) Rotate given view direction by R to get a ray
# 5) Cast ray to get distance dist to wall in the ray's direction
# 6) Calculate depth of wall given the distance and ray's angle theta
#       depth = dist * cos theta
# 7) Calculate height of the wall 

_COLUMN_MIDPOINTS = (map(mean, zip(_COLUMN_BOUNDARIES, _COLUMN_BOUNDARIES[1:])))
    # distances are sampled for the middle of each column
_COLUMN_DIST_TO_SCREEN = _SCREEN_MID / math.tan(0.5 * _FOV_R)  # 1
_COLUMN_ANGLES = tuple(
    math.atan((x - _SCREEN_MID) / _COLUMN_DIST_TO_SCREEN)
    for x in _COLUMN_MIDPOINTS
)  # 2
_COLUMN_ROT_MATS = tuple(map(M2.rot, _COLUMN_ANGLES))  # 3
_COLUMN_COSINES = tuple(map(math.cos, _COLUMN_ANGLES))  # for 6


# Floor maths:
# Inputs: screen size (SS), vertical FOV (vFOV)
# 1) Calculate distance between camera and view plane (view_dist):
#       view_dist = SS / ( 2tan(vFOV/2) )
# 2) Calculate vertical angle (theta) given height on screen/view plane (y)
#       theta = atan( (SS/2 - y) / view_dist )
# 3) Calculate depth of world point given vertical angle theta
#       depth = SS / ( 2 tan theta )
#             = SS / ( 2 ( (SS/2 - y) / view_dist ))
#             = (SS * dist) / (2y - SS)
#             = (SS/2 * dist) / (y - SS/2)
# 4) Calculate distance to floor point given its depth and horizontal angle phi
#       dist = depth / cos phi
# 5) Calculate x, y position of floor point given position, ray and distance
#       x, y = pos + dist * ray

_ROW_MIDPOINTS = map(mean, zip(_ROW_BOUNDARIES, _ROW_BOUNDARIES[1:]))
_VIEW_PLANE_DIST = SCREEN_SIZE / (2 * math.tan(0.5 * _V_FOV_R)) * 0.1
    # TODO: the maths does NOT account for the 0.1, but for some reason
    # it makes the image way more correct. Figure it oot
    # TODO rename
    # TODO join with other plane dist?
_ROW_DEPTHS = (
    (_SCREEN_MID * _VIEW_PLANE_DIST) / (y - _SCREEN_MID)
    for y in _ROW_MIDPOINTS
)
_FLOOR_PIXEL_DISTS = tuple(
    depth / cos
    for depth in _ROW_DEPTHS
    for cos in _COLUMN_COSINES
)  # final result (this is huge)
_FLOOR_RECTS = tuple(
    pygame.Rect(
        _COLUMN_BOUNDARIES[j],
        _ROW_BOUNDARIES[i+1],  # first row boundary is bottom of screen
        _COLUMN_WIDTH_DRAW,
        _ROW_HEIGHT_DRAW,
    )
    for i in range(ROW_COUNT)
    for j in range(COLUMN_COUNT)
)  # not sure how much time this actually saves
_FLOOR_SHADING = tuple(_DARKENER(dist) for dist in _FLOOR_PIXEL_DISTS)
    # TODO: add shading to floor in a nice way


# entities
PLAYER_HEIGHT = 1
_PLAYER_CIRCLE_SCREEN_HEIGHT_MULT = 0.5 * SCREEN_SIZE * _VIEW_PLANE_DIST
    # this is hard to explain but the maths checks out, promise

print(f'3d precomp finished in {round(time.time()-_t, 3)}s')


def xy_nonvec_calc(dist, pos_x, pos_y, ray_x, ray_y):
    return pos_x + dist*ray_x, pos_y + dist*ray_y


def draw_world(screen, field, player):
    screen.fill(BACKGROUND._value)
    pos, view = player.position, player.direction
    rays = tuple(rot_mat @ view for rot_mat in _COLUMN_ROT_MATS)

    # floor
    flat_input_data = tuple(
        (dist, *pos, *ray)
        for dist, ray in zip(_FLOOR_PIXEL_DISTS, cycle(rays))
    )
    floor_positions = tuple(starmap(xy_nonvec_calc, flat_input_data))
        # TODO: fix distances and skip big ones here
    for i in range(ROW_COUNT * COLUMN_COUNT):
        x, y = floor_positions[i]
        if max(abs(x-1000), abs(y-1000)) > 1100: continue
        #if x<=-5 or y<=-5 or x>=2005 or y>=2005: continue  # TODO: make this nicer
        pygame.draw.rect(
            screen,
            _FLOOR_COLOUR(x, y),
            _FLOOR_RECTS[i],
        )

    # walls
    for ray, cos, left in zip(rays, _COLUMN_COSINES, _COLUMN_BOUNDARIES):
        dist = field.cast_ray_at_wall(pos, ray)
        depth = dist * cos
        # TODO: rethink with depth = view dot ray
        wall_height = min(
            40 * SCREEN_SIZE / depth,  # TODO: magic number multiplier
            SCREEN_SIZE,
        )
        col_top = _SCREEN_MID - 0.5 * wall_height
        wall = pygame.Rect(
            left,
            col_top,
            _COLUMN_WIDTH_DRAW,
            wall_height,
        )
        wall_colour = (WALL_COLOUR * _DARKENER(dist))._value
        pygame.draw.rect(screen, wall_colour, wall)
    draw_crosshair(screen)


def draw_crosshair(screen):
    pygame.draw.line(
        screen,
        CROSSHAIR_COLOUR,
        (_SCREEN_MID, _SCREEN_MID + CROSSHAIR_SIZE),
        (_SCREEN_MID, _SCREEN_MID - CROSSHAIR_SIZE),
    )  # vertical
    pygame.draw.line(
        screen,
        CROSSHAIR_COLOUR,
        (_SCREEN_MID + CROSSHAIR_SIZE, _SCREEN_MID),
        (_SCREEN_MID - CROSSHAIR_SIZE, _SCREEN_MID),
    )  # horizontal
    pygame.draw.circle(
        screen,
        CROSSHAIR_COLOUR,
        (_SCREEN_MID, _SCREEN_MID),
        0.6 * CROSSHAIR_SIZE,
        1
    )  # circle


def draw_entity(screen, entity, colour, player):
    if entity is player: return  # don't draw self
    p = player.position
    e = entity.position
    p2e = e - p
    v = player.direction
    depth = p2e @ v

    if FOV_D < 180 and depth < 0: return  # fast FOV check
        # don't draw entities behind you if FOV is forward-facing

    dist = p2e.length
    dist_inv = 1 / dist

    phi = 0 if depth > dist else math.acos(depth * dist_inv)
    if 2 * phi > _FOV_R: return  # outside FOV

    x1, y1 = p2e
    x2, y2 = v
    if x1*y2 > x2*y1:  # v nice solve, 3rd component of cross product
        phi = -phi

        # x-coord of middle of player
    y_pos = _SCREEN_MID + (_VIEW_PLANE_DIST * _SCREEN_MID * dist_inv)
    #    # y-coord of centre of ellipse on floor

    phi_sides = math.atan(10 * e.size * dist_inv)
        # angle between p2e and p2(edges of circle)
    left_x  = _SCREEN_MID + _COLUMN_DIST_TO_SCREEN * math.tan(phi - phi_sides)
    mid_x   = _SCREEN_MID + _COLUMN_DIST_TO_SCREEN * math.tan(phi)
    right_x = _SCREEN_MID + _COLUMN_DIST_TO_SCREEN * math.tan(phi + phi_sides)
        # I couldn't not align these

    y_offset = 40 * _SCREEN_MID / depth  # TODO fix magic number from wall

    #pygame.draw.circle(screen, colour._value, (x_pos,_SCREEN_MID), 10)
    #return

    colour = (_DARKENER(dist) * colour)._value

    pygame.draw.polygon(screen, colour, (
        (left_x,  _SCREEN_MID),
        (mid_x,   _SCREEN_MID + y_offset),  # bottom
        (right_x, _SCREEN_MID),
        (mid_x,   _SCREEN_MID - y_offset * 0.5),  # top
    ))  # main shape
    pygame.draw.polygon(screen, colour, (
        (left_x,  _SCREEN_MID + y_offset),  # bottom left
        (mid_x,   _SCREEN_MID + y_offset * 0.8),  # top
        (right_x, _SCREEN_MID + y_offset),  # bottom right
    ))  # stand triangle
    pygame.draw.line(
        screen,
        '#2e3436',
        (left_x,  _SCREEN_MID),
        (right_x, _SCREEN_MID),
    )  # line in the middle
    pygame.draw.circle(
        screen,
        '#cc0000',
        (mid_x,  _SCREEN_MID + y_offset),
        2
    )  # bottom circle


def draw_projectile(screen, proj, player, *args, **kwargs):
    p = player.position
    start = proj.position + -5*proj.velocity
    end = proj.position + 5*proj.velocity

    p2s = start - p
    p2e = end - p
    v = player.direction

    s_depth = p2s @ v
    e_depth = p2e @ v

    if FOV_D < 180 and (s_depth < 0 or e_depth < 0):
        return  # skip if everything behind you
        # TODO draw if one in front and one behind

    s_dist = p2s.length
    e_dist = p2e.length

    s_phi = 0 if s_depth > s_dist else math.acos(s_depth / s_dist)
    e_phi = 0 if e_depth > e_dist else math.acos(e_depth / e_dist)

    sx, sy = start
    ex, ey = end
    vx, vy = v
    if sx*vy > vx*sy: s_phi *= -1
    if ex*vy > vx*ey: e_phi *= -1

    s_pos = _SCREEN_MID + _COLUMN_DIST_TO_SCREEN * math.tan(s_phi)
    e_pos = _SCREEN_MID + _COLUMN_DIST_TO_SCREEN * math.tan(e_phi)

    pygame.draw.line(
        screen,
        proj.colour,
        (s_pos,  _SCREEN_MID),
        (e_pos, _SCREEN_MID),
        width=1+int(proj.size * 200 / e_depth)
    )  # line









