import socket
from math import cos, sin, pi
from threading import Thread

import OpenGL  # not used but i don't dare removing it
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *  # not used but i don't dare removing it

from matrixx import Vector as V
from random import randint as r
from field import *

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
        return  # yes grisha i know that the else is no needed but i think it adds clarity
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


def iterate():
    glViewport(0, 0, SCREEN_SIZE, SCREEN_SIZE)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, SCREEN_SIZE, 0.0, SCREEN_SIZE, 0.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def showScreen():
    global field
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    iterate()
    self_ball = field.players[SELF_INDEX]
    draw_background(field, self_ball)
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


def client_tick():
    global field
    if TIMEOUT:
        while TIMEOUT:
            return

    forward = KEYS_PRESSED[0] - KEYS_PRESSED[2]
    turn = KEYS_PRESSED[1] - KEYS_PRESSED[3]
    shoot = KEYS_PRESSED[4]
    field.steer(SELF_INDEX, turn, forward, shoot)
    data = bytearray(3)
    data[0] = turn + 1
    data[1] = forward + 1
    data[2] = shoot
    if forward or turn or shoot:
        UDPClientSocket.sendto(data, serverAddressPort)

    status = field.tick(SELF_INDEX)
    '''for s in status:
        if s == WALL_COLLISION:
            sound1.play()
        if s == OTHER_COLLISION:
            sound2.play()
        if s == SELF_HIT:
            sound3.play()
        if s == TARGET_HIT:
            sound4.play()
        if s == JOIN:
            sound5.play()'''

    showScreen()
    '''
    index = 0
    ai_player = field.players[index]
    target = ai_player.target
    target_dir = (target.position + target.velocity * 60 + target.direction * target.acceleration * 60 - ai_player.position)
    current_dir = ai_player.direction
    direction = int(current_dir[0] * target_dir[1] - current_dir[1] * target_dir[0])
    field.steer(index, direction, 1)
    '''


def game_thread(field):
    global TIMEOUT, SELF_INDEX
    while 1:
        try:
            received_byes = UDPClientSocket.recvfrom(bufferSize)[0]
            SELF_INDEX = received_byes[-1]
            received_byes = received_byes[:-1]
            field.from_bytes(received_byes)
            if TIMEOUT:
                print('\nRestored')
                TIMEOUT = 0
        except socket.timeout:
            if TIMEOUT == 0:
                print('timeout', end='d')
            else:
                server_connect(field)
            SELF_INDEX = -1
            TIMEOUT += 1


def server_connect(field):
    self_index = -1
    while self_index == -1:
        try:
            UDPClientSocket.sendto(b'0x00', serverAddressPort)
            received_byes = UDPClientSocket.recvfrom(bufferSize)[0]
            self_index = received_byes[-1]
            field.self_index = SELF_INDEX
            received_byes = received_byes[:-1]
            field.from_bytes(received_byes)
        except socket.timeout:
            print('.', end='')
    return self_index


if __name__ == '__main__':
    print('Create game')
    field = Field()
    # pygame.init()
    '''
    sound1 = pygame.mixer.Sound('resources/sound1.ogg')
    sound2 = pygame.mixer.Sound('resources/sound2.ogg')
    sound3 = pygame.mixer.Sound('resources/sound3.ogg')
    sound4 = pygame.mixer.Sound('resources/sound4.ogg')
    sound5 = pygame.mixer.Sound('resources/sound5.ogg')
    '''
    print('Logging into server', end='')
    SELF_INDEX = server_connect(field)
    print('\nFetching game from server')
    thread = Thread(target=game_thread, args=(field,))
    thread.start()
    print('Setting up open GL')
    glutInit()
    glutInitDisplayMode(GLUT_RGBA)
    glutInitWindowSize(SCREEN_SIZE, SCREEN_SIZE)
    glutInitWindowPosition(300, 75)
    wind = glutCreateWindow("Socket Find")
    glutDisplayFunc(showScreen)
    glutIdleFunc(client_tick)
    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutMainLoop()
    print('start Game')
