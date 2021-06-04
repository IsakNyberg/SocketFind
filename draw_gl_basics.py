from math import cos, sin, tau

import OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *


def set_colour(colour):
    glColor3f(*colour)


def draw_line(v_start, v_end, colour):
    set_colour(colour)
    glBegin(GL_LINES)
    glVertex2f(*v_start)
    glVertex2f(*v_end)
    glEnd()


CIRCLE_SIZE_S = 3
CIRCLE_SIZE_M = 16
CIRCLE_SIZE_L = 32
CIRCLE_S = tuple(
    (cos(phi), sin(phi))
    for phi in (i * tau / CIRCLE_SIZE_S for i in range(CIRCLE_SIZE_S))
)
CIRCLE_M = tuple(
    (cos(phi), sin(phi))
    for phi in (i * tau / CIRCLE_SIZE_M for i in range(CIRCLE_SIZE_M))
)
CIRCLE_L = tuple(
    (cos(phi), sin(phi))
    for phi in (i * tau / CIRCLE_SIZE_L for i in range(CIRCLE_SIZE_L))
)


def draw_circle(p_x, p_y, colour, size=30):
    set_colour(colour)
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


def draw_rect(bl_x, bl_y, w, h, colour):
    set_colour(colour)
    glBegin(GL_POLYGON)
    glVertex2f(bl_x, bl_y)
    glVertex2f(bl_x + w, bl_y)
    glVertex2f(bl_x + w, bl_y + h)
    glVertex2f(bl_x, bl_y + h)
    glEnd()
