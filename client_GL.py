import time
import socket
from math import *
from threading import Thread

import OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from matrixx import Vector as V
import pygame

from field import *
import display
import display_proj
print('Import successful.')

serverAddressPort = ('85.229.18.138', 63834)
serverAddressPort = ('localhost', 63834)
bufferSize = 1024

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(1)
SELF_COLOUR = V([0xff, 0xb9, 0x17])
TARGET_COLOUR = V([0x19, 0xff, 0xc1])
WEAKNESS_COLOUR = V([0xcc, 0x47, 0x81])
COOL_DOWN_COLOUR = V([0xff, 0xf7, 0x8a])
OTHER_COLOUR = V([0x6c, 0x55, 0xe0])
TIMEOUT = 0
SCREEN_SIZE = 800
SELF_INDEX = -1


def circle(p_x, p_y, size=30):
    sides = 32
    glBegin(GL_POLYGON)
    for i in range(sides):  # Circle
        x = cos(i * 2 * pi / sides) * size + p_x
        y = sin(i * 2 * pi / sides) * size + p_y
        glVertex2f(x, y)
    glEnd()


def draw_player(entity, colour=OTHER_COLOUR, perspective=None):
    # perspective is a player object
    r, g, b = (colour * (1 / 255))._value  # colour
    glColor3f(r, g, b)

    size = entity.size  # body
    p_x = entity.position[0]
    p_y = entity.position[1]
    circle(p_x, p_y, size)

    front_x = p_x + size * entity.direction[0] * 1.5
    front_y = p_y + size * entity.direction[1] * 1.5
    o_x, o_y = entity.direction[1] * size, entity.direction[0] * size

    glBegin(GL_POLYGON)  # Nose
    for x, y in [(p_x - o_x, p_y + o_y), (p_x + o_x, p_y - o_y), (front_x, front_y)]:
        glVertex2f(x, y)
    glEnd()


def iterate():
    glViewport(0, 0, SCREEN_SIZE, SCREEN_SIZE)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, SCREEN_SIZE, 0.0, SCREEN_SIZE, 0.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def showScreen():
    global field, self_ball
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    iterate()
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
        draw_player(player, colour=colour)

    glutSwapBuffers()


def client_tick():
    global field
    field.tick()
    showScreen()
    index = 0
    ai_player = field.players[index]
    target = ai_player.target
    target_dir = (
                target.position + target.velocity * 60 + target.direction * target.acceleration * 60 - ai_player.position)
    current_dir = ai_player.direction
    direction = int(current_dir[0] * target_dir[1] - current_dir[1] * target_dir[0])
    field.steer(index, direction, 1)
    index = 1
    ai_player = field.players[index]
    target = ai_player.target
    target_dir = (
            target.position + target.velocity * 60 + target.direction * target.acceleration * 60 - ai_player.position)
    current_dir = ai_player.direction
    direction = int(current_dir[0] * target_dir[1] - current_dir[1] * target_dir[0])
    field.steer(index, direction, 1)
    index = 2
    ai_player = field.players[index]
    target = ai_player.target
    target_dir = (
            target.position + target.velocity * 60 + target.direction * target.acceleration * 60 - ai_player.position)
    current_dir = ai_player.direction
    direction = int(current_dir[0] * target_dir[1] - current_dir[1] * target_dir[0])
    field.steer(index, direction, 1)


if __name__ == '__main__':
    print('Create game')
    field = Field()
    for _ in range(9):
        field.new_player()
    print('Logging into server', end='')
    #server_connect()
    print('\nFetching game from server')
    #thread = Thread(target=game_thread, args=(field, ))
    #thread.start()
    self_ball = field.players[0]
    print('Setting up open GL')
    glutInit()
    glutInitDisplayMode(GLUT_RGBA)
    glutInitWindowSize(800, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow("Socket Find")
    glutDisplayFunc(showScreen)
    glutIdleFunc(client_tick)
    glutMainLoop()
    print('start Game')




