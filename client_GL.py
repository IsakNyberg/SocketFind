import socket
from threading import Thread

from field import *
import draw_gl_topdown
import draw_gl_raycast

print('Import successful.')

disp_mod = draw_gl_topdown
draw_frame = disp_mod.draw_frame

serverAddressPort = ('85.229.18.138', 63834)
serverAddressPort = ('localhost', 63834)
bufferSize = 1024

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(1)


TIMEOUT = 0
SELF_INDEX = -1


def client_tick():
    global field
    while TIMEOUT:
        pass

    forward = draw_gl_topdown.KEYS_PRESSED[0] - draw_gl_topdown.KEYS_PRESSED[2]
    turn = draw_gl_topdown.KEYS_PRESSED[1] - draw_gl_topdown.KEYS_PRESSED[3]
    shoot = draw_gl_topdown.KEYS_PRESSED[4]
    field.steer(SELF_INDEX, turn, forward, shoot)
    data = bytearray(3)
    data[0] = turn + 1
    data[1] = forward + 1
    data[2] = shoot
    if forward or turn or shoot:
        UDPClientSocket.sendto(data, serverAddressPort)
    status = field.tick(SELF_INDEX)
    '''for s in status: SOUNDS
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
    draw_frame(field, SELF_INDEX)
    import time
    time.sleep(1/120)
    '''  AI
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
                print('timeout', end='')
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
    draw_gl_topdown.init(field, SELF_INDEX, client_tick)
    print('start Game')
