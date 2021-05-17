import pygame
import socket
from threading import Thread
from display import *
from field import *

serverAddressPort = ("13.90.90.170", 63834)
bufferSize = 1024
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)


def get_keys():
    keys = pygame.key.get_pressed()
    x = 0
    y = 0
    if keys[pygame.K_w]:
        y += -1
    if keys[pygame.K_a]:
        x += -1
    if keys[pygame.K_s]:
        y += 1
    if keys[pygame.K_d]:
        x += 1
    return x, y


def game_thread(field):
    while 1:
        received_byes = UDPClientSocket.recvfrom(bufferSize)
        field.from_bytes(received_byes[0])


if __name__ == '__main__':
    field = Field()
    field.new_player()
    UDPClientSocket.sendto(b'0x00', serverAddressPort)
    self_index = int.from_bytes(UDPClientSocket.recvfrom(bufferSize)[0], 'big')
    field.self_index = self_index
    thread = Thread(target=game_thread, args=(field, ))
    thread.start()

    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont('Comic Sans MS', 30)

    screen = pygame.display.set_mode([MAX_POSITION_X, MAX_POSITION_Y])
    tick = 0
    running = True
    clock = pygame.time.Clock()
    while running:
        keys = get_keys()
        while len(field.entities) == 0:
            pass

        field.steer(0, *keys)
        data = bytearray()
        data.append(keys[0]+1)
        data.append(keys[1]+1)
        UDPClientSocket.sendto(data, serverAddressPort)

        field.tick()
        tick += 1
        clock.tick(128)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((255, 255, 255))
        weakness = field.entities[self_index].weakness
        for e in field.entities:
            x = e.x_position
            y = e.y_position
            if e.name == self_index:
                pygame.draw.circle(screen, 'green', (x, y), e.size)
                pygame.draw.line(screen, 'green', (x, y), (x + e.x_velocity * 40, y + e.y_velocity * 40))
                pygame.draw.line(screen, 'blue', (x, y), (x + e.x_acceleration * 50, y + e.y_acceleration * 50))
            elif e.name == weakness:
                pygame.draw.circle(screen, 'red', (x, y), e.size)
            else:
                pygame.draw.circle(screen, 'blue', (x, y), e.size)
        text_surface = font.render(f'Score: {field.entities[self_index].score}/{field.score}', False, (0, 0, 0))
        screen.blit(text_surface, (10, 10))
        pygame.display.flip()

