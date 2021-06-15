import pygame

import weapons


pygame.font.init()
FONT = pygame.font.SysFont('Comic Sans MS', 20)


WEAPON_COUNT = len(weapons.WEAPON_LOOKUP)
WEAPON_ICONS = tuple(
    pygame.image.load(f'resources/w_icon_{i}.png')  # TODO: convert?
    for i in range(1, WEAPON_COUNT+1)
)
WEAPON_MINI_ICONS = tuple(
    pygame.image.load(f'resources/w_icon_{i}_mini.png')
    for i in range(1, WEAPON_COUNT+1)
)  # TODO: draw icons with pygame with optional scaling?


def draw_gui(screen, field, me):
    width, height = screen.get_size()
    my_score_surf = FONT.render(
        f'Score: {me.score}',
        True,
        '#d3d7cf',
    )
    screen.blit(my_score_surf, (5, 0))

    f_score_surf = FONT.render(
        f'Field Score: {field.score}',
        True,
        '#d3d7cf',
    )
    screen.blit(f_score_surf, (5, 25))

    screen.blit(
        WEAPON_MINI_ICONS[(me.weapon_index + 1) % WEAPON_COUNT],
        (width - 5 - 20, 15),
    )

    screen.blit(
        WEAPON_ICONS[(me.weapon_index) % WEAPON_COUNT],
        (width - 5 - 20 - 5 - 50, 5),
    )

    screen.blit(
        WEAPON_MINI_ICONS[(me.weapon_index - 1) % WEAPON_COUNT],
        (width - 5 - 20 - 5 - 50 - 5 - 20, 15),
    )
