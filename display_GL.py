import OpenGL  # not used but i don't dare removing it
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *  # not used but i don't dare removing it

from math import cos, sin, pi
from random import randint as r

from matrixx import Vector as V
from field import *

SELF_COLOUR = V([0xff, 0xb9, 0x17])
TARGET_COLOUR = V([0x19, 0xff, 0xc1])
WEAKNESS_COLOUR = V([0xcc, 0x47, 0x81])
COOL_DOWN_COLOUR = V([0xff, 0xf7, 0x8a])
OTHER_COLOUR = V([0x6c, 0x55, 0xe0])
SCREEN_SIZE = 800


def line(v_start, v_end):
    glBegin(GL_LINES)
    glVertex2f(*v_start)
    glVertex2f(*v_end)
    glEnd()


circle_sides = 3
CIRCLE_S = tuple((cos(i * 2 * pi / circle_sides), sin(i * 2 * pi / circle_sides)) for i in range(circle_sides))
circle_sides = 16
CIRCLE_M = tuple((cos(i * 2 * pi / circle_sides), sin(i * 2 * pi / circle_sides)) for i in range(circle_sides))
circle_sides = 32
CIRCLE_L = tuple((cos(i * 2 * pi / circle_sides), sin(i * 2 * pi / circle_sides)) for i in range(circle_sides))
def circle(p_x, p_y, size=30):
    if size < 10:
        circumference = CIRCLE_S
    elif size < 20:
        circumference = CIRCLE_M
    else:
        circumference = CIRCLE_L

    glBegin(GL_POLYGON)
    for x, y in circumference:  # Circle
        x = x * size + p_x
        y = y * size + p_y
        glVertex2f(x, y)
    glEnd()


def draw_player(entity, colour, perspective):
    r, g, b = (colour * (1 / 255))._value  # colour
    glColor3f(r, g, b)

    x_offset = perspective.position[0]
    y_offset = perspective.position[1]

    p_x = entity.position[0]
    p_y = entity.position[1]
    size = entity.size  # body
    draw_size = size + SCREEN_SIZE
    if abs(p_x - x_offset) > draw_size:
        return  # yes grisha i know that the else is no needed but i think it adds clarity
    if abs(p_y - y_offset) > draw_size:
        return
    else:
        p_x -= x_offset - SCREEN_SIZE // 2
        p_y -= y_offset - SCREEN_SIZE // 2
        circle(p_x, p_y, size)

    front_x = p_x + size * entity.direction[0] * 1.5 + entity.velocity[0] * 3 * entity.cool_down / 100
    front_y = p_y + size * entity.direction[1] * 1.5 + entity.velocity[1] * 3 * entity.cool_down / 100
    o_x, o_y = entity.direction[1] * size, entity.direction[0] * size

    glBegin(GL_POLYGON)  # Nose
    for x, y in [(p_x - o_x, p_y + o_y), (p_x + o_x, p_y - o_y), (front_x, front_y)]:
        glVertex2f(x, y)
    glEnd()


def draw_projectile(projectile, perspective):
    offset = perspective.position - Vector((SCREEN_SIZE // 2, SCREEN_SIZE // 2))
    x_offset = perspective.position[0]
    y_offset = perspective.position[1]

    p_x = projectile.position[0]
    p_y = projectile.position[1]
    if abs(p_x - x_offset) > SCREEN_SIZE:
        return  # yes Grisha i know that the else is no needed but i think it adds clarity
    if abs(p_y - y_offset) > SCREEN_SIZE:
        return
    else:
        start = (projectile.position + projectile.velocity*5 - offset)
        end = (projectile.position - projectile.velocity*5 - offset)
        glColor3f(0.9, 0.5, 0.1)
        line(start.to_tuple(), end.to_tuple())


total_stars = 200
stars = tuple(Vector((r(-300, MAX_POSITION), r(-300, MAX_POSITION))) for _ in range(total_stars))
def draw_background(field, perspective):
    glColor3f(0.7, 0.3, 0.4)
    pos = perspective.position - V((SCREEN_SIZE // 2, SCREEN_SIZE // 2))
    for start, end in field.walls:
        start_perspective = start - pos
        end_perspective = end - pos
        line(start_perspective.to_tuple(), end_perspective.to_tuple())

    glColor3f(0.8, 0.8, 1)
    for star in stars:
        if abs(star[0] - pos[0]) > SCREEN_SIZE:
            continue
        elif abs(star[1] - pos[1]) > SCREEN_SIZE:
            continue
        circle(*star-(pos*0.5), 2)


def draw_scope(field, perspective):
    glColor3f(0.9, 0.1, 0.1)
    start = Vector((SCREEN_SIZE // 2, SCREEN_SIZE // 2))
    end = start + perspective.direction*(SCREEN_SIZE//2)
    line(start, end)


def iterate():
    glViewport(0, 0, SCREEN_SIZE, SCREEN_SIZE)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, SCREEN_SIZE, 0.0, SCREEN_SIZE, 0.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def showScreen(field, SELF_INDEX):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    iterate()
    self_ball = field.players[SELF_INDEX]
    draw_background(field, self_ball)
    draw_scope(field, self_ball)
    for projectile in field.projectiles:
        draw_projectile(projectile, self_ball)
    for player in field.players:
        if player.cool_down:
            colour = COOL_DOWN_COLOUR
        elif player is self_ball:
            colour = SELF_COLOUR
        elif player.target is self_ball:
            colour = WEAKNESS_COLOUR
        elif player is self_ball.target:
            colour = TARGET_COLOUR
        else:
            colour = OTHER_COLOUR
        draw_player(player, colour, self_ball)
    glutSwapBuffers()


KEYS_PRESSED = [0, 0, 0, 0, 0]  # wasd e
def key_down(*args):
    global KEYS_PRESSED
    if args[0].lower() == b'w':
        KEYS_PRESSED[0] = 1
    if args[0].lower() == b'a':
        KEYS_PRESSED[1] = 1
    if args[0].lower() == b's':
        KEYS_PRESSED[2] = 1
    if args[0].lower() == b'd':
        KEYS_PRESSED[3] = 1
    if args[0].lower() == b'e':
        KEYS_PRESSED[4] = 1


def key_up(*args):
    global KEYS_PRESSED
    if args[0].lower() == b'w':
        KEYS_PRESSED[0] = 0
    if args[0].lower() == b'a':
        KEYS_PRESSED[1] = 0
    if args[0].lower() == b's':
        KEYS_PRESSED[2] = 0
    if args[0].lower() == b'd':
        KEYS_PRESSED[3] = 0
    if args[0].lower() == b'e':
        KEYS_PRESSED[4] = 0

def init(field, SELF_INDEX, client_tick):
    glutInit()
    glutInitDisplayMode(GLUT_RGBA)
    glutInitWindowSize(SCREEN_SIZE, SCREEN_SIZE)
    glutInitWindowPosition(300, 75)
    wind = glutCreateWindow("Socket Find")
    glutDisplayFunc(iterate)
    glutIdleFunc(client_tick)
    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutMainLoop()