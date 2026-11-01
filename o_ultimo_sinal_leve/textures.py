# Texturas e fundos gerados por código (sem imagens). Tudo é feito uma vez ao carregar o capítulo.
import math
import random
import pygame

TS = 64
SHADES = 12
FULL = set("#BDGX")


def _c(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def _paint(fn, seed):
    rnd = random.Random(seed)
    s = pygame.Surface((TS, TS))
    for y in range(TS):
        for x in range(TS):
            r, g, b = fn(x, y, rnd)
            s.set_at((x, y), (_c(r), _c(g), _c(b)))
    return s


# ------------------------------------------------------------------ casa
def wallpaper(x, y, rnd):
    n = rnd.randint(-5, 5)
    if y >= 46:
        grain = 9 if (x * 3 + y // 4) % 11 == 0 else 0
        r, g, b = 78 - grain, 52 - grain, 38 - grain
        if y in (46, 47):
            r, g, b = 130, 100, 70
        return r + n, g + n, b + n
    stripe = 9 if (x // 8) % 2 else 0
    r, g, b = 112 - stripe, 88 - stripe, 72 - stripe
    if x % 16 in (3, 4) and y % 20 in (8, 9):
        r, g, b = r - 24, g - 28, b - 20
    if 36 <= x <= 44 and y < 34:
        k = (1 - abs(x - 40) / 5.0) * (1 - y / 40.0)
        if k > 0:
            r, g, b = r - 34 * k, g - 30 * k, b - 26 * k
    return r + n, g + n, b + n


BOOKS = [(120, 40, 40), (40, 70, 112), (60, 92, 50), (132, 102, 40), (92, 50, 102), (52, 52, 58), (112, 72, 40)]


def bookshelf(x, y, rnd):
    n = rnd.randint(-4, 4)
    if x < 3 or x > 60 or y % 16 >= 14:
        return 86 + n, 58 + n, 36 + n
    idx = ((x // 4) * 7 + (y // 16) * 3) % 7
    gap = (idx * 2 + (y // 16)) % 5 + 3
    if (y % 16) < gap:
        return 28 + n, 20 + n, 16 + n
    r, g, b = BOOKS[idx]
    if x % 4 == 0:
        r, g, b = r * 0.7, g * 0.7, b * 0.7
    return r + n, g + n, b + n


# -------------------------------------------------------------- hospital
def hosp_tile(x, y, rnd):
    n = rnd.randint(-5, 5)
    if y < 4:
        return 196 + n, 204 + n, 200 + n
    if y >= 50:
        return 62 + n, 110 + n, 96 + n
    r, g, b = 170, 184, 178
    if x % 16 == 0 or y % 16 == 0:
        r, g, b = 118, 132, 128
    if y > 38:
        r, g, b = r - 14, g - 14, b - 14
    if 20 <= x <= 25 and 10 <= y < 44 and (y + x) % 7 < 3:
        r, g, b = r - 30, g - 34, b - 36
    return r + n, g + n, b + n


def hosp_window(x, y, rnd):
    n = rnd.randint(-3, 3)
    if x < 6 or x > 57 or y < 8 or y > 48:
        return 150 + n, 160 + n, 158 + n
    r, g, b = 16, 24, 30
    if (x + y) % 38 < 5:
        r, g, b = r + 26, g + 30, b + 34
    if 30 < x < 34:
        r, g, b = 130, 138, 138
    return r + n, g + n, b + n


# ------------------------------------------------------------------ poço
def stone(x, y, rnd):
    row = y // 16
    off = 8 if row % 2 else 0
    bx = (x + off) % 32
    n = rnd.randint(-6, 6)
    if y % 16 < 2 or bx < 2:
        return 34 + n, 36 + n, 40 + n
    h = ((x + off) // 32 * 37 + row * 91) % 29 - 14
    r, g, b = 86 + h, 90 + h, 98 + h
    if y % 16 > 12 and rnd.random() > 0.55:
        r, g, b = r - 14, g + 6, b - 14
    return r + n, g + n, b + n


def rune(x, y, rnd):
    n = rnd.randint(-5, 5)
    r, g, b = 70 + n, 74 + n, 82 + n
    d = math.hypot(x - 31.5, y - 31.5)
    if abs(d - 20) < 1.6 or (abs(x - 31.5) < 1.4 and d < 20) or (abs(y - 31.5) < 1.4 and d < 20):
        return 70, 200, 210
    return r, g, b


# ---------------------------------------------------------------- origem
def static(x, y, rnd):
    v = rnd.randint(14, 70)
    if (y // 3) % 7 == 0:
        v += 26
    return v + 10, v - 4, v + 18


def hazard(x, y, rnd):
    n = rnd.randint(-5, 5)
    if ((x + y) // 8) % 2:
        return 150 + n, 30 + n, 30 + n
    return 24 + n, 20 + n, 28 + n


# ---------------------------------------------------------- comuns / objetos
def make_door(base, window):
    def fn(x, y, rnd):
        n = rnd.randint(-4, 4)
        r, g, b = base
        if x < 3 or x > 60 or y < 2:
            r, g, b = r * 0.55, g * 0.55, b * 0.55
        elif x % 16 in (0, 1):
            r, g, b = r * 0.78, g * 0.78, b * 0.78
        if window and 20 < x < 44 and 8 < y < 28:
            return 14 + n, 20 + n, 24 + n
        if not window and ((10 < x < 28 or 36 < x < 54) and (8 < y < 26 or 34 < y < 56)) and \
                (x in (10, 27, 36, 53) or y in (8, 25, 34, 55)):
            r, g, b = r * 0.6, g * 0.6, b * 0.6
        if 48 <= x <= 53 and 30 <= y <= 38:
            return 200 + n, 170 + n, 70 + n
        return r + n, g + n, b + n
    return fn


def gate(x, y, rnd):
    n = rnd.randint(-4, 4)
    if 28 <= x <= 36 and 28 <= y <= 40:
        return 176 + n, 40 + n, 40 + n
    if x % 12 in (4, 5, 6) or 18 <= y <= 21 or 44 <= y <= 47:
        k = 20 if x % 12 == 5 else 0
        return 106 + k + n, 108 + k + n, 118 + k + n
    return 18 + n, 14 + n, 16 + n


def exit_closed(x, y, rnd):
    n = rnd.randint(-3, 3)
    if x < 4 or x > 59 or y < 3:
        return 54 + n, 54 + n, 64 + n
    if abs(x - y) < 2 or abs(x + y - 63) < 2:
        return 90 + n, 22 + n, 22 + n
    return 10 + n, 10 + n, 14 + n


def exit_open(x, y, rnd):
    d = math.hypot(x - 31.5, y - 31.5) / 45.0
    k = max(0.0, 1.0 - d)
    ring = 28 if int(d * 22) % 3 == 0 else 0
    return 40 + 190 * k + ring, 70 + 170 * k + ring, 140 + 110 * k + ring


def crate(x, y, rnd):
    n = rnd.randint(-5, 5)
    border = x < 4 or x > 59 or y < 4 or y > 59
    brace = abs(x - y) < 3
    plank = y % 16 == 0
    if border or brace or plank:
        return 92 + n, 62 + n, 36 + n
    return 150 + n + (6 if (x // 8) % 2 else 0), 108 + n, 62 + n


def tall(x, y, rnd):
    n = rnd.randint(-4, 4)
    if y > 52 and ((x + y) // 6) % 2:
        return 200 + n, 170 + n, 40 + n
    if y > 52:
        return 26 + n, 26 + n, 28 + n
    if x < 3 or x > 60 or y < 3:
        return 62 + n, 68 + n, 76 + n
    if (x in (8, 55)) and (y % 14 == 6):
        return 150 + n, 156 + n, 164 + n
    r = 100 + n + (8 if x % 8 < 2 else 0)
    return r, r + 6, r + 14


THEMES = {
    "house": dict(wall=(wallpaper, 11), alt=(bookshelf, 12), door=make_door((122, 72, 44), False),
                  tint=(1.0, 0.90, 0.78),
                  floor=((14, 10, 9), (52, 36, 26)), ceil=((10, 9, 10), (34, 30, 28)),
                  top_crate=(150, 112, 70), top_tall=(120, 126, 136), pit=(3, 3, 4), lip=(70, 54, 40)),
    "hospital": dict(wall=(hosp_tile, 21), alt=(hosp_window, 22), door=make_door((84, 124, 108), True),
                     tint=(0.86, 1.0, 0.96),
                     floor=((12, 16, 15), (64, 76, 72)), ceil=((10, 12, 12), (52, 58, 56)),
                     top_crate=(150, 112, 70), top_tall=(120, 126, 136), pit=(2, 4, 4), lip=(70, 84, 80)),
    "well": dict(wall=(stone, 31), alt=(rune, 32), door=make_door((74, 78, 86), False),
                 tint=(0.80, 0.92, 1.0),
                 floor=((8, 10, 13), (42, 48, 58)), ceil=((6, 7, 9), (26, 28, 34)),
                 top_crate=(150, 112, 70), top_tall=(120, 126, 136), pit=(1, 1, 3), lip=(70, 90, 100)),
    "origin": dict(wall=(static, 41), alt=(hazard, 42), door=make_door((92, 40, 92), False),
                   tint=(1.0, 0.80, 1.0),
                   floor=((10, 6, 12), (50, 24, 54)), ceil=((8, 4, 10), (38, 14, 36)),
                   top_crate=(150, 112, 70), top_tall=(120, 126, 136), pit=(4, 0, 6), lip=(120, 40, 120)),
}


def _variants(base, tint):
    out = []
    for lvl in range(SHADES):
        f = max(0.07, (1.0 - lvl / float(SHADES)) ** 1.35)
        for side in (0, 1):
            k = f * (0.72 if side else 1.0)
            s = base.copy()
            s.fill((_c(255 * k * tint[0]), _c(255 * k * tint[1]), _c(255 * k * tint[2])),
                   special_flags=pygame.BLEND_RGB_MULT)
            out.append(s)
    return out


def build(theme_name):
    th = THEMES[theme_name]
    tint = th["tint"]
    base = {
        "#": _paint(*th["wall"]),
        "B": _paint(*th["alt"]),
        "D": _paint(th["door"], 51),
        "G": _paint(gate, 52),
        "X": _paint(exit_closed, 53),
        "x": _paint(exit_open, 54),
        "c": _paint(crate, 55),
        "T": _paint(tall, 56),
    }
    return {k: _variants(v, tint) for k, v in base.items()}


def make_background(theme_name, rw, rh, proj):
    """Teto + chão numa superfície 3x mais alta; o horizonte fica em 1.5*rh."""
    th = THEMES[theme_name]
    s = pygame.Surface((rw, 3 * rh))
    mid = int(1.5 * rh)
    f0, f1 = th["floor"]
    c0, c1 = th["ceil"]
    tint = th["tint"]
    for y in range(3 * rh):
        if y < mid:
            k = (mid - y) / float(mid)
            col = [c0[i] + (c1[i] - c0[i]) * k for i in range(3)]
        else:
            o = y - mid + 1
            k = (y - mid) / float(3 * rh - mid)
            col = [f0[i] + (f1[i] - f0[i]) * (k ** 0.8) for i in range(3)]
            dist = 0.62 * proj / o
            if int(dist) % 2 == 0:
                col = [v * 0.88 for v in col]
        s.fill((_c(col[0]), _c(col[1]), _c(col[2])), (0, y, rw, 1))
    return s


def make_vignette(rw, rh):
    sw, sh = max(8, rw // 4), max(8, rh // 4)
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            nx = (x + 0.5 - sw / 2.0) / (sw / 2.0)
            ny = (y + 0.5 - sh / 2.0) / (sh / 2.0)
            r2 = nx * nx * 0.75 + ny * ny * 1.1
            a = int(min(205, max(0.0, r2 - 0.30) * 215))
            small.set_at((x, y), (0, 0, 0, a))
    return pygame.transform.smoothscale(small, (rw, rh))
