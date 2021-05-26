import pygame
import math
import random
import display
import bisect
import time
from field import MAX_POSITION
from matrix import Matrix as M, Vector as V

DISPLAY_ID = 2

BACKGROUND = '#111111'
WALL_COLOUR = V([0x36, 0x36, 0x36])

SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'

DARK_TILE = WALL_COLOUR
LITE_TILE = V([0x66, 0x66, 0x66])#V([0x33, 0x33, 0x33])

# light
LIGHT_MIN = 0.4  # between 0 and 0.5, do NOT put 0.5 or higher here please
LIGHT_HALF_LIFE = 700
_LIGHT_C = LIGHT_MIN  # light intensity: f(x) = a/(x^2+b) + c
_LIGHT_B = LIGHT_HALF_LIFE**2 * (1 - 2*_LIGHT_C)  # maths checks out, I promise
_LIGHT_A = _LIGHT_B * (1-_LIGHT_C)
_DARKENER = lambda x: _LIGHT_A/(x**2 + _LIGHT_B) + _LIGHT_C

# walls
FOV_D = 100  # deg
DEG_PER_COL = 2
WALL_HEIGHT_MULTIPLIER = 50
ENTITY_HEIGHT = 0.7  # relative to a wall
_FOV_R = math.radians(FOV_D)
_FOV_R_INV = 1 / _FOV_R
_FOV_R_HALF = 0.5 * _FOV_R
factory = lambda x: M([[math.cos(x), -math.sin(x)], [math.sin(x), math.cos(x)]])
phis = tuple(map(math.radians, range(-FOV_D//2, 1 + FOV_D//2, DEG_PER_COL)))
coss = tuple(map(math.cos, phis))
rot_mats = tuple(map(factory, phis))

# floor
V_FOV_D = 90  # deg
FLOOR_LINE_COUNT = 100
FLOOR_CHECKERBOARD_SIZE = 500
FLOOR_CAMERA_HEIGHT = 100
FLOOR_SAMPLING_ANGLE = 0.01  # rad
_V_FOV_R = math.radians(V_FOV_D)
_V_FOV_R_INV = 1 / _V_FOV_R
_V_FOV_R_HALF = 0.5 * _V_FOV_R
_LOWEST_ANGLE_M = -_V_FOV_R_HALF  # between bottom of screen and horizontal
_LOWEST_ANGLE_B = 0.5*math.pi - _V_FOV_R_HALF  # same but with vertical
_FLOOR_CAMERA_HEIGHT_INV = 1 / FLOOR_CAMERA_HEIGHT
_FLOOR_SAMPLING_ANGLE_INV = 1 / FLOOR_SAMPLING_ANGLE
_FLOOR_SAMPLING_PARTIAL_DISTANCES = [
    FLOOR_CAMERA_HEIGHT * math.tan(_LOWEST_ANGLE_B + i*FLOOR_SAMPLING_ANGLE)
    for i in range(1+int(_V_FOV_R_HALF / FLOOR_SAMPLING_ANGLE))
]  # distance to sampling point for every angle (starting with lowest)
_FLOOR_CHECKERBOARD = lambda x, y: (x//FLOOR_CHECKERBOARD_SIZE + y//FLOOR_CHECKERBOARD_SIZE) % 5  # TODO change back to 2
_FLOOR_LINE_COUNT_INV = 1 / FLOOR_LINE_COUNT
_FLOOR_CHECKERBOARD_COLOURS_1 = {
    0: '#ff0000',
    1: '#00ff00',
    2: '#0000ff',
    3: '#ff00ff',
    4: '#00ffff',
}
_FLOOR_CHECKERBOARD_COLOURS_2 = {
    0: '#75507b',
    1: '#f57900',
    2: '#ad7fa8',
    3: '#4e9a06',
    4: '#8f5902',
}
_FLOOR_CHECKERBOARD_COLOURS_3 = {
    0: '#000000',
    1: '#528783',
    2: '#140658',
    3: '#346048',
    4: '#918563',
}

_FLOOR_2_SAMPLING_INTERDISTNACES = [
    _FLOOR_SAMPLING_PARTIAL_DISTANCES[i+1] - _FLOOR_SAMPLING_PARTIAL_DISTANCES[i]
    for i in range(len(_FLOOR_SAMPLING_PARTIAL_DISTANCES)-1)
]
_FLOOR_2_SAMPLING_MIDPOINTS = [
    0.5 * (_FLOOR_SAMPLING_PARTIAL_DISTANCES[i+1] + _FLOOR_SAMPLING_PARTIAL_DISTANCES[i])
    for i in range(len(_FLOOR_SAMPLING_PARTIAL_DISTANCES)-1)
]

_FLOOR_3_SCREEN_SIZE = 800  # TODO think of a better way to get this number
_FLOOR_3_SCREEN_SIZE_HALF = _FLOOR_3_SCREEN_SIZE // 2

FLOOR_3_V_FOV_D = 90  # deg
_FLOOR_3_V_FOV_R = math.radians(FLOOR_3_V_FOV_D)
FLOOR_3_ROW_COUNT = 50  # how many rows on bottom half of screen
#FLOOR_3_VIEW_PLANE_DIST = 10  # units TODO: extract this value from vert FOV
_FLOOR_3_DIST_TO_VIEW_PLANE = _FLOOR_3_SCREEN_SIZE_HALF / math.tan(_FLOOR_3_V_FOV_R / 2)

_FLOOR_3_SCREEN_HEIGHT_TO_V_ANGLE = lambda y: math.atan(
    (_FLOOR_3_SCREEN_SIZE_HALF - y) / _FLOOR_3_DIST_TO_VIEW_PLANE
)  # this gives the positive angle without direction
_FLOOR_3_ROW_HEIGHTS = _FLOOR_3_SCREEN_SIZE_HALF / FLOOR_3_ROW_COUNT
_FLOOR_3_ROW_BOUNDARY_ANGLES = tuple(map(
    _FLOOR_3_SCREEN_HEIGHT_TO_V_ANGLE,
    (
        i*_FLOOR_3_ROW_HEIGHTS
        for i in range(FLOOR_3_ROW_COUNT)
    )
))
_FLOOR_3_SAMPLING_DEPTHS = tuple(
    0.5 * (_FLOOR_3_ROW_BOUNDARY_ANGLES[i] + _FLOOR_3_ROW_BOUNDARY_ANGLES[i-1])
    for i in range(1, len(_FLOOR_3_ROW_BOUNDARY_ANGLES))
)




def angle_to_coord(screen_size, x_rad, y_rad):
    # takes radian angles from forward vector (middle of screen)
    # positive angles go to top right
    x = screen_size * (x_rad*_FOV_R_INV + 0.5)
    y = screen_size * (y_rad*_V_FOV_R_INV - 0.5)
    return x, y


def draw_world(screen, field, player, screen_size):
    screen.fill(BACKGROUND)
    #screen.fill("#203c1e", (0, screen_size//2, screen_size, screen_size//2))
    #screen.fill('#0000ff')
    pos, view = player.position, player.direction
    col_width = screen_size / len(rot_mats)
    col_width_draw = col_width + 1  # for overlap
    screen_mid = screen_size // 2

    for i, (cos, rot_mat) in enumerate(zip(coss, rot_mats)):
        # wall
        ray = rot_mat @ view
        dist = field.cast_ray_at_wall(pos, ray)
        depth = dist * cos
        wall_height = min(
            screen_size * WALL_HEIGHT_MULTIPLIER / depth,
            screen_size,
        )
        x_pos = i * col_width
        col_top = screen_mid - wall_height * 0.5
        wall = pygame.Rect(
            x_pos,
            col_top,
            col_width_draw,
            wall_height,
        )
        dark_mult = _DARKENER(dist)
        wall_colour = (dark_mult * WALL_COLOUR).to_list()

        pygame.draw.rect(screen, wall_colour, wall)
        if not col_top:
            continue  # don't draw floor if wall takes up screen


        # checkerboard floor
        '''floor = [(None, 0)]  # list of tuples: tuples (colour, units)
        units_total = 0
        #cur_pos = pos.copy()  # TODO
        for i, dist_to_midpoint in enumerate(_FLOOR_2_SAMPLING_MIDPOINTS):
            cur_pos = pos + dist_to_midpoint * ray
            x, y = cur_pos
            #floor_colour = LITE_TILE if _FLOOR_CHECKERBOARD(x, y) else DARK_TILE
            #floor_colour = floor_colour.to_list()
            floor_colour = _FLOOR_CHECKERBOARD_COLOURS_1[_FLOOR_CHECKERBOARD(x, y)]
            #floor_colour = floor_colour * _DARKENER(dist_to_midpoint)
            last_colour, last_units = floor[-1]
            if last_colour == floor_colour:
                floor[-1] = (last_colour, last_units+1)
            else:
                floor.append((floor_colour, 1))
            units_total += 1
            if dist_to_midpoint > dist:
                break
        cur_top = screen_size
        step_top = col_top / units_total
        for floor_colour, floor_units in floor[1:]:
            height = floor_units * step_top
            cur_top -= height
            sq = pygame.Rect(x_pos, cur_top-1, col_width_draw, height+1)
            pygame.draw.rect(screen, floor_colour, sq)'''

        # ALSO WORKS!
        '''if col_top and (sampling_count:=bisect.bisect(_FLOOR_SAMPLING_PARTIAL_DISTANCES, dist)):
            # don't draw floor if wall took whole screen
            cur_top = screen_size
            step_top = col_top / sampling_count
            wall_bottom = col_top + wall_height
            cur_pos = pos.copy()

            for j in range(1, int(sampling_count) + 2):
                top = screen_size - j*step_top
                dist_to_point = _FLOOR_SAMPLING_PARTIAL_DISTANCES[j]
                dist_since_last = dist_to_point - _FLOOR_SAMPLING_PARTIAL_DISTANCES[j-1]
                cur_pos += dist_since_last * ray
                x, y = cur_pos
                floor_colour = _FLOOR_CHECKERBOARD_COLOURS_2[_FLOOR_CHECKERBOARD(x, y)]
                #floor_colour = LITE_TILE if _FLOOR_CHECKERBOARD(x, y) else DARK_TILE
                #floor_colour = floor_colour * _DARKENER(dist_to_point)
                sq = pygame.Rect(x_pos, top, col_width_draw, step_top + 1)
                pygame.draw.rect(screen, floor_colour, sq)
                if top < wall_bottom: break'''

        
        '''total_theta = math.atan(dist * _FLOOR_CAMERA_HEIGHT_INV) - _LOWEST_ANGLE_B
            # angle between lower FOV and to bottom of wall
        sampling_count = total_theta * _FLOOR_SAMPLING_ANGLE_INV  # add ceil
        cur_top = screen_size
        step_top = col_top / sampling_count
        wall_bottom = col_top + wall_height
        cur_pos = pos.copy()

        for j in range(1, int(sampling_count) + 2):
            top = screen_size - j*step_top
            dist_to_point = _FLOOR_SAMPLING_PARTIAL_DISTANCES[j]
            dist_since_last = dist_to_point - _FLOOR_SAMPLING_PARTIAL_DISTANCES[j-1]
            cur_pos += dist_since_last * ray
            x, y = cur_pos
            floor_colour = _FLOOR_CHECKERBOARD_COLOURS_3[_FLOOR_CHECKERBOARD(x, y)]
            ##floor_colour = LITE_TILE if _FLOOR_CHECKERBOARD(x, y) else DARK_TILE
            #floor_colour = floor_colour * _DARKENER(dist_to_point)
            sq = pygame.Rect(x_pos, top, col_width_draw, step_top + 1)
            pygame.draw.rect(screen, floor_colour, sq)
            if top < wall_bottom: break'''

        
        
        
    '''
    print(t_first, t_second, t_third)
    5.093006372451782
    4.449524164199829
    4.2408607006073'''

        # draw wall after floor
        # pygame.draw.rect(screen, wall_colour, wall)


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

    colour = (_DARKENER(dist) * colour).to_list()

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




