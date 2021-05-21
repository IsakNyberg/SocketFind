import pygame

from display import *
from field import *


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


if __name__ == '__main__':
    field = Field()
    for i in range(5):
        field.new_player()

    pygame.init()
    screen = pygame.display.set_mode([MAX_POSITION, MAX_POSITION])

    running = True
    clock = pygame.time.Clock()
    while running:
        clock.tick(120)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        field.tick()
        for i in range(len(field.players)):
            x = field.players[(i + 1) % len(field.players)].x_position - field.players[(i - 1) % len(field.players)].x_position
            y = field.players[(i + 1) % len(field.players)].y_position - field.players[(i - 1) % len(field.players)].y_position
            field.steer(i, x, y)
        field.steer(1, *get_keys())
        screen.fill((255, 255, 255))
        for e in field.players:
            x = e.x_position
            y = e.y_position
            pygame.draw.circle(screen, 'red', (x, y), e.size)

            pygame.draw.line(screen, 'green', (x, y), (x + e.x_velocity * 40, y + e.y_velocity * 40))
            pygame.draw.line(screen, 'blue', (x, y), (x + e.x_acceleration * 50, y + e.y_acceleration * 50))

        pygame.display.flip()

