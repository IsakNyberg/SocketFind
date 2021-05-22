import pygame
import socket
from threading import Thread
from field import *
import display

serverAddressPort = ('85.229.18.138', 63834)
bufferSize = 1024

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(1)
BACKGROUND = '#000000'
BG = pygame.image.load("resources/bg.jpg")
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
COOL_DOWN_COLOUR = '#fff78a'
TIMEOUT = 0
SCREEN_SIZE = 800
SELF_INDEX = -1


def get_keys():
    keys = pygame.key.get_pressed()
    turn = 0
    forward = 0
    if keys[pygame.K_w]:
        forward += 1
    if keys[pygame.K_a]:
        turn += -1
    if keys[pygame.K_s]:
        forward -= 1
    if keys[pygame.K_d]:
        turn += 1
    return turn, forward


def game_thread(field):
    global TIMEOUT, SELF_INDEX
    while 1:
        try:
            received_byes = UDPClientSocket.recvfrom(bufferSize)
            field.from_bytes(received_byes[0])
            if TIMEOUT:
                print('\nRestored')
                TIMEOUT = 0
        except socket.timeout:
            if TIMEOUT == 0:
                print('timeout')
            else:
                print('.', end='')
            SELF_INDEX = -1
            server_connect()
            TIMEOUT += 1


def server_connect():
    global SELF_INDEX, field
    while SELF_INDEX == -1:
        try:
            UDPClientSocket.sendto(b'0x00', serverAddressPort)
            message = UDPClientSocket.recvfrom(bufferSize)[0]
            if len(message) != 1:
                continue
            SELF_INDEX = int.from_bytes(message, 'big')
            field.self_index = SELF_INDEX

            received_byes = UDPClientSocket.recvfrom(bufferSize)
            field.from_bytes(received_byes[0])
        except socket.timeout:
            print('.', end='')


if __name__ == '__main__':
    print('Create game')
    field = Field()
    field.new_player()

    print('Logging into server', end='')
    server_connect()
    print('\nFetching game from server')
    thread = Thread(target=game_thread, args=(field, ))
    thread.start()

    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont('Comic Sans MS', 30)
    sound1 = pygame.mixer.Sound('resources/sound1.ogg')
    sound2 = pygame.mixer.Sound('resources/sound2.ogg')
    sound3 = pygame.mixer.Sound('resources/sound3.ogg')
    sound4 = pygame.mixer.Sound('resources/sound4.ogg')
    sound5 = pygame.mixer.Sound('resources/sound5.ogg')
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode([SCREEN_SIZE, SCREEN_SIZE])
    tick = 0
    running = True
    print('start Game')
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # get steering data and send to server
        keys = get_keys()
        field.steer(SELF_INDEX, *keys)
        data = bytearray()
        data.append(keys[0]+1)
        data.append(keys[1]+1)
        UDPClientSocket.sendto(data, serverAddressPort)

        clock.tick(128)
        tick += 1

        if TIMEOUT:
            while TIMEOUT:
                pass

        status = field.tick(SELF_INDEX)
        for s in status:
            if s == WALL_COLLISION:
                sound1.play()
            if s == OTHER_COLLISION:
                sound2.play()
            if s == WEAKNESS_COLLISION:
                sound3.play()
            if s == POINT_COLLISION:
                sound4.play()
            if s == JOIN:
                sound5.play()

        screen.fill(BACKGROUND)
        weakness = field.players[SELF_INDEX].weakness
        offset_x = field.players[SELF_INDEX].position[0] - SCREEN_SIZE // 2
        offset_y = field.players[SELF_INDEX].position[1] - SCREEN_SIZE // 2
        screen.blit(BG, (-offset_x, -offset_y))

        for e in field.players:
            if e.cool_down:
                display.draw_entity(screen, e, colour=COOL_DOWN_COLOUR, offset_x=offset_x, offset_y=offset_y)
            elif e.name == SELF_INDEX:
                display.draw_entity(screen, e, colour=SELF_COLOUR, offset_x=offset_x, offset_y=offset_y)
            elif e.name == weakness:
                display.draw_entity(screen, e, colour=WEAKNESS_COLOUR, offset_x=offset_x, offset_y=offset_y)
            else:
                display.draw_entity(screen, e, colour=OTHER_COLOUR, offset_x=offset_x, offset_y=offset_y)

        text_surface = font.render(f'Score: {field.players[SELF_INDEX].score}/{field.score}', False, (0xff, 0xff, 0xff))
        screen.blit(text_surface, (10, 10))
        pygame.display.flip()

