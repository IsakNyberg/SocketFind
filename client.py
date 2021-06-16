import time
import socket
from threading import Thread

import pygame
from matrixx import Vector as V

from field import *
import draw_topdown, draw_raycast
from draw_gui import draw_gui
from constants import SCREEN_SIZE, HALF_SCREEN
import action


serverAddressPort = ('85.229.18.138', 63834)
serverAddressPort = ('localhost', 63834)
bufferSize = 1024

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(5)
SELF_COLOUR = V([0x1c, 0xff, 0x91])
TARGET_COLOUR = V([0x19, 0xff, 0xc1])
WEAKNESS_COLOUR = V([0xcc, 0x47, 0x81])
OTHER_COLOUR = V([0x6c, 0x55, 0xe0])
COOL_DOWN_COLOUR = V([0xff, 0xf7, 0x8a])
TIMEOUT = 0
SELF_INDEX = -1

# toggle this between display and display_proj
DISPLAY = draw_raycast
DISPLAY_ID = DISPLAY.DISPLAY_ID


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
                print('timeout', end='')
            else:
                SELF_INDEX = server_connect(field)
            SELF_INDEX = -1
            TIMEOUT += 1


def server_connect(field):
    self_index = -1
    while self_index == -1:
        try:
            UDPClientSocket.sendto(b'0x00', serverAddressPort)
            received_byes = UDPClientSocket.recvfrom(bufferSize)[0]
            self_index = received_byes[-1]
            received_byes = received_byes[:-1]
            field.from_bytes(received_byes)
        except socket.timeout:
            print('.', end='')
    return self_index


if __name__ == '__main__':
    print('Create game')
    field = Field()
    print('Logging into server', end='')
    SELF_INDEX = server_connect(field)
    print('\nFetching game from server')
    thread = Thread(target=game_thread, args=(field, ))
    thread.start()

    pygame.init()
    sound1 = pygame.mixer.Sound('resources/sound1.ogg')
    sound2 = pygame.mixer.Sound('resources/sound2.ogg')
    sound3 = pygame.mixer.Sound('resources/sound3.ogg')
    sound4 = pygame.mixer.Sound('resources/sound4.ogg')
    sound5 = pygame.mixer.Sound('resources/sound5.ogg')
    clock = pygame.time.Clock()

    cur_actions = action.ActionStatus()

    screen = pygame.display.set_mode([SCREEN_SIZE*2, SCREEN_SIZE])
    surfaceL = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE))
    surfaceR = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE))
    tick = 0
    running = True
    print('start Game')
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        clock.tick(128)
        tick += 1

        # get steering data and send to server
        cur_actions.update_from_pygame(pygame.key.get_pressed())
        field.steer(SELF_INDEX, *cur_actions.as_tuple)
        UDPClientSocket.sendto(
            cur_actions.as_byte,
            serverAddressPort,
        )

        status = field.tick(SELF_INDEX)
        if tick % 3 == 0:
            continue

        for s in status:
            if s == WALL_COLLISION:
                #sound1.play()
                pass
            if s == OTHER_COLLISION:
                sound2.play()
            if s == SELF_HIT:
                sound3.play()
            if s == TARGET_HIT:
                sound4.play()
            if s == JOIN:
                sound5.play()

        me = field.players[SELF_INDEX]
        draw_topdown.draw_frame(surfaceL, field, me)
        draw_raycast.draw_frame(surfaceR, field, me)

        screen.blit(surfaceL, (0, 0))
        screen.blit(surfaceR, (SCREEN_SIZE, 0))

        draw_gui(screen, field, me)
        pygame.display.update()

