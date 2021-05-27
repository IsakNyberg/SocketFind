import math
from multiprocessing import Pool
from itertools import starmap

import pygame
from matrixx import Matrix as M, Vector as V

import display
from field import MAX_POSITION


DISPLAY_ID = 2

BACKGROUND = '#111111'
WALL_COLOUR = V((0x36, 0x36, 0x36))

SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'

DARK_TILE = V((0x20, 0x3c, 0x1e))
LITE_TILE = DARK_TILE * 1.2
IMAGE = pygame.image.load("resources/bg2.jpg")

SCREEN_SIZE = 800

# light
LIGHT_MIN = 0.4  # between 0 and 0.5, do NOT put 0.5 or higher here please
LIGHT_HALF_LIFE = 700
_LIGHT_C = LIGHT_MIN  # light intensity: f(x) = a/(x^2+b) + c
_LIGHT_B = LIGHT_HALF_LIFE**2 * (1 - 2*_LIGHT_C)  # maths checks out, I promise
_LIGHT_A = _LIGHT_B * (1-_LIGHT_C)
_DARKENER = lambda x: _LIGHT_A/(x**2 + _LIGHT_B) + _LIGHT_C

# walls
FOV_D = 100  # deg
DEG_PER_COL = 1
WALL_HEIGHT_MULTIPLIER = 50
ENTITY_HEIGHT = 0.7  # relative to a wall
_FOV_R = math.radians(FOV_D)
_FOV_R_INV = 1 / _FOV_R
_FOV_R_HALF = 0.5 * _FOV_R
_ROTATION_MATR_MAKER = lambda x: M([[math.cos(x), -math.sin(x)], [math.sin(x), math.cos(x)]])
_HORIZONTAL_ANGLES = tuple(map(math.radians, range(-FOV_D//2, 1 + FOV_D//2, DEG_PER_COL)))
_H_ANGLE_COSINES = tuple(map(math.cos, _HORIZONTAL_ANGLES))
_H_ANGLE_MAT_ROTATORS = tuple(map(_ROTATION_MATR_MAKER, _HORIZONTAL_ANGLES))
_COLUMN_COUNT = len(_H_ANGLE_MAT_ROTATORS)  # TODO: make this togglable, remove DEG_PER_COL
_COLUMN_WIDTH = SCREEN_SIZE / _COLUMN_COUNT
_COLUMN_WIDTH_DRAW = _COLUMN_WIDTH + 1
_COLUMN_POSITIONS = tuple(i * _COLUMN_WIDTH for i in range(FOV_D // DEG_PER_COL +1))
_SCREEN_MID = SCREEN_SIZE // 2


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
# 4) Calculate distance to floor point given its depth and horizontal angle phi
#       dist = depth / cos phi
# 5) Calculate x, y position of floor point given position, ray and distance
#       x, y = pos + dist * ray

FLOOR_ROW_COUNT = 50
SCREEN_SIZE = 800
V_FOV_D = 90
_V_FOV_R = math.radians(V_FOV_D)
_VIEW_PLANE_DIST = SCREEN_SIZE / (2 * math.tan(0.5 * _V_FOV_R)) * 0.1
    # TODO: the maths does NOT account for the 0.1, but for some reason
    # it makes the image way more correct. Figure it oot
_FLOOR_ROW_HEIGHT = 0.5 * SCREEN_SIZE / FLOOR_ROW_COUNT
_FLOOR_ROW_HEIGHT_DRAW = _FLOOR_ROW_HEIGHT + 1
_FLOOR_SAMPLE_HEIGHT_BORDERS = tuple(
    SCREEN_SIZE - i*_FLOOR_ROW_HEIGHT for i in range(FLOOR_ROW_COUNT + 1)
)
_FLOOR_ROW_POSITIONS = tuple(_FLOOR_SAMPLE_HEIGHT_BORDERS[1:-1])
    # skip the first bc it's zero
    # skip the last bc it's SS/2 which causes DBZ
'''_FLOOR_SAMPLE_HEIGHT_MIDPOINTS = tuple(
    0.5 * (_FLOOR_SAMPLE_HEIGHT_BORDERS[i-1] + _FLOOR_SAMPLE_HEIGHT_BORDERS[i])
    for i in range(1, len(_FLOOR_SAMPLE_HEIGHT_BORDERS))
)
_FLOOR_ROW_DEPTHS = tuple(
    (SCREEN_SIZE - 2*y) / (SCREEN_SIZE * _VIEW_PLANE_DIST)
    for y in _FLOOR_SAMPLE_HEIGHT_MIDPOINTS
)'''  # TODO
_FLOOR_ROW_DEPTHS = tuple(
    (SCREEN_SIZE * _VIEW_PLANE_DIST) / (2*y - SCREEN_SIZE)
    for y in _FLOOR_ROW_POSITIONS
)
_FLOOR_ROW_COLUMN_DISTS = tuple(
    tuple(depth/cos for cos in _H_ANGLE_COSINES)
    for depth in _FLOOR_ROW_DEPTHS
)  # final result (this is huge)
_FLOOR_ROW_COLUMN_SHADERS = tuple(
    tuple(_DARKENER(dist) for dist in row)
    for row in _FLOOR_ROW_COLUMN_DISTS
)  # overkill, but we have more memory than processing speed so might as well

FLOOR_CHECKERBOARD_SIZE = 500
_FLOOR_CHECKERBOARD = lambda x, y: (x//FLOOR_CHECKERBOARD_SIZE + y//FLOOR_CHECKERBOARD_SIZE) % 2



def xy_nonvec_calc(dist, pos_x, pos_y, ray_x, ray_y):
    return pos_x + dist*ray_x, pos_y + dist*ray_y


def draw_world(screen, field, player, screen_size):
    screen.fill(BACKGROUND)
    #screen.fill("#203c1e", (0, screen_size//2, screen_size, screen_size//2))
    #screen.fill('#0000ff')
    pos, view = player.position, player.direction
    rays = [rot_mat @ view for rot_mat in _H_ANGLE_MAT_ROTATORS]

    # calc walls
    wall_dists = tuple(field.cast_ray_at_wall(pos, ray) for ray in rays)

    # calc & draw floor
    floor_positions = None
    '''with Pool(2) as pool:
        floor_positions = pool.starmap(
            xy_nonvec_calc,
            tuple(
                (dist, *pos._value, *ray._value)
                for dists in _FLOOR_ROW_COLUMN_DISTS
                for dist, ray in zip(dists, rays)
            )
        )'''  # multiprocessing version
    floor_positions = tuple(starmap(
        xy_nonvec_calc,
        tuple(
            (dist, *pos._value, *ray._value)
            for dists in _FLOOR_ROW_COLUMN_DISTS
            for dist, ray in zip(dists, rays)
        )  # TODO: fix distances and skip big ones here
    ))
    for i, dists in enumerate(_FLOOR_ROW_COLUMN_DISTS):
        for j, dist in enumerate(dists):
            #if dist > wall_dists[j]: continue  # TODO fix distances so this works
            x, y = floor_positions[len(rays)*i + j]  # TODO iterate over flat tuple?
            if x<0 or y<0 or x>2000 or y>2000:
                continue  # TODO: make this nicer
            #dark = _FLOOR_ROW_COLUMN_SHADERS[i][j]
            #floor_colour = LITE_TILE if _FLOOR_CHECKERBOARD(x, y) else DARK_TILE
            #floor_colour = (floor_colour * dark)._value
            floor_colour = IMAGE.get_at((int(x), int(y)))
            sq = pygame.Rect(
                _COLUMN_POSITIONS[j],
                _FLOOR_ROW_POSITIONS[i],  # TODO: why is the floor on the ceiling?
                _COLUMN_WIDTH_DRAW,
                _FLOOR_ROW_HEIGHT_DRAW,
            )
            pygame.draw.rect(screen, floor_colour, sq)

    # draw walls
    for j, (dist, cos) in enumerate(zip(wall_dists, _H_ANGLE_COSINES)):
        # TODO: change walls to same geometric system as floor
        # wall_xy = xy_nonvec_calc(dist, *pos._value, *rays[j]._value)
        depth = dist * cos
        wall_height = min(
            SCREEN_SIZE * WALL_HEIGHT_MULTIPLIER / depth,
            SCREEN_SIZE,
        )
        col_top = _SCREEN_MID - wall_height * 0.5
        wall = pygame.Rect(
            _COLUMN_POSITIONS[j],
            col_top,
            _COLUMN_WIDTH_DRAW,
            wall_height,
        )
        dark_mult = _DARKENER(dist)
        wall_colour = (dark_mult * WALL_COLOUR)._value

        pygame.draw.rect(screen, wall_colour, wall)


def draw_entity(screen, entity, colour, screen_size, player):
    # "minimap"
    # display.draw_entity(screen, entity, colour, **kwargs, mini=True)

    if entity is player: return
    p = player.position
    e = entity.position
    p2e = e - p
    v = player.direction
    dot = p2e @ v

    if FOV_D < 180 and dot < 0: return
    # don't draw entities behind you if FOV is forward-facing

    dist = p2e.length
    phi = math.acos(min(1, dot / dist))  # assumes v.length is 1
    if 2*phi > _FOV_R: return
    # outside FOV

    x1, y1 = p2e
    x2, y2 = v
    if x1*y2 - x2*y1 > 0:  # v nice solve, 3rd component of cross product
        phi = -phi  # figure out if e left or right of p2e

    depth = dist * math.cos(phi)
    wall_height = min(screen_size, screen_size * 50 / depth)
    entity_height = ENTITY_HEIGHT*wall_height

    exposition = screen_size*(phi+(_FOV_R/2))/_FOV_R
    x_offset = 1000*entity.size//2 / depth
    bot = screen_size//2 + wall_height//2
    top = bot - entity_height

    colour = (_DARKENER(dist) * colour)._value

    pygame.draw.polygon(screen, colour, [
        (exposition + x_offset, bot),
        (exposition - x_offset, bot),
        (exposition, top),
    ])
    ellipse_height = 5 + 5000/depth
    rect = pygame.Rect(
        exposition - x_offset,
        bot - ellipse_height/2,
        2 * x_offset,
        ellipse_height,
    )
    pygame.draw.ellipse(screen, colour, rect)


    #pygame.draw.circle(screen, colour, (exposition, screen_size/2), size)




