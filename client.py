import pygame
import socket
from threading import Thread
from field import *
import display

serverAddressPort = ("localhost", 63834)
bufferSize = 1024

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(2)
BACKGROUND = '#363638'
SELF_COLOUR = '#1cff91'
WEAKNESS_COLOUR = '#cc4781'
OTHER_COLOUR = '#6c55e0'
TIMEOUT = 0


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
    global TIMEOUT
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
            TIMEOUT += 1


def server_connect():
    self_index = -1
    while self_index == -1:
        try:
            UDPClientSocket.sendto(b'0x00', serverAddressPort)
            self_index = int.from_bytes(UDPClientSocket.recvfrom(bufferSize)[0], 'big')
            field.self_index = self_index

            received_byes = UDPClientSocket.recvfrom(bufferSize)
            field.from_bytes(received_byes[0])
        except socket.timeout:
            print('.', end='')
    return self_index


if __name__ == '__main__':
    print('Create game')
    field = Field()
    field.new_player()

    print('Logging into server', end='')
    self_index = server_connect()
    print('\nFetching game from server')
    thread = Thread(target=game_thread, args=(field, ))
    thread.start()

    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont('Comic Sans MS', 30)
    sound1 = pygame.mixer.Sound('resources/sound1.mp3')
    sound2 = pygame.mixer.Sound('resources/sound2.mp3')
    sound3 = pygame.mixer.Sound('resources/sound3.mp3')
    sound4 = pygame.mixer.Sound('resources/sound4.mp3')
    sound5 = pygame.mixer.Sound('resources/sound5.mp3')
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode([MAX_POSITION_X, MAX_POSITION_Y])
    tick = 0
    running = True
    print('start Game')
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # get steering data and send to server
        keys = get_keys()
        field.steer(self_index, *keys)
        data = bytearray()
        data.append(keys[0]+1)
        data.append(keys[1]+1)
        UDPClientSocket.sendto(data, serverAddressPort)

        clock.tick(128)
        tick += 1

        if TIMEOUT:
            while TIMEOUT:
                pass
            self_index = server_connect()

        status = field.tick(self_index)
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
        weakness = field.entities[self_index].weakness
        for e in field.entities:
            x = e.x_position
            y = e.y_position
            if e.name == self_index:
                display.draw_entity(screen, e, colour=SELF_COLOUR)
            elif e.name == weakness:
                display.draw_entity(screen, e, colour=WEAKNESS_COLOUR)
            else:
                display.draw_entity(screen, e, colour=OTHER_COLOUR)
        text_surface = font.render(f'Score: {field.entities[self_index].score}/{field.score}', False, (0, 0, 0))
        screen.blit(text_surface, (10, 10))
        pygame.display.flip()

