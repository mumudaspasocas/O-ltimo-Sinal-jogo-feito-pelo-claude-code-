"""O ÚLTIMO SINAL — Edição Leve 2.0
Terror psicológico em primeira pessoa, renderizado por raycasting na CPU (sem OpenGL).
Novidades: olhar para cima/baixo, pulo, corrida, parkour, chaves, portas, puzzle de
interruptores, sombra perseguidora, sanidade, texturas procedurais, sons gerados por código.
"""
import math
import random
import sys

import pygame

import audio
import textures
from story import CHAPTERS, ENDINGS, PROLOGUE, WHISPERS
from world import LEVELS

FULL = textures.FULL
SHADES = textures.SHADES
TS = textures.TS

BH = {"c": 0.5, "T": 1.0}          # altura das caixas
WALL_H = 2.0                       # altura das paredes
EYE = 0.68                         # altura dos olhos
STEP = 0.12                        # degrau que dá para subir andando
GRAV = 11.0
JUMP_V = 4.3
WALK = 2.5
RUN = 4.1
MAXD = 20.0
SHADE_DIST = 12.0
MOUSE_X = 0.0022
MOUSE_Y = 0.0016
QUALITY = [(256, 144), (320, 180), (400, 225), (480, 270)]
QUALITY_NAMES = ["Mínima", "Baixa", "Média", "Alta"]

SWITCH_COLORS = {
    "azul": (70, 130, 240), "vermelho": (225, 60, 60), "verde": (70, 210, 100),
    "branco": (240, 240, 240),
}


def wrap(text, font, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= maxw or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("O ÚLTIMO SINAL — Edição Leve 2.0")
        self.screen = pygame.display.set_mode((1152, 648), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.audio = audio.Audio()
        self.fonts_h = 0
        self.build_fonts()
        self.t = 0.0
        self.state = "title"
        self.qi = 2
        self.fov = 73
        self.show_fps = False
        self.show_help = True
        self.fps_acc = 0.0
        self.fps_n = 0
        self.fps_now = 0.0
        self.auto_quality = True
        self.look = 0.0
        self.bob = 0.0
        self.flick = 0
        self.rand = random.Random()
        self.sanity = 100.0
        self.deaths = 0
        self.total_memories = 0
        self.scaled = None
        self.message = ""
        self.message_t = 0.0
        self.read_title = ""
        self.read_text = ""
        self.read_t = 0.0
        self.page_lines = []
        self.page_title = ""
        self.page_t = 0.0
        self.page_done = None
        self.ending_key = "good"
        self.pending_open = False
        self.set_quality(self.qi)
        self.load_level(0)
        self.set_state("title")

    # ------------------------------------------------------------ utilidades
    def build_fonts(self):
        h = self.screen.get_height()
        self.fonts_h = h
        self.f_title = pygame.font.Font(None, max(36, int(h * 0.14)))
        self.f_big = pygame.font.Font(None, max(28, int(h * 0.075)))
        self.f_mid = pygame.font.Font(None, max(20, int(h * 0.046)))
        self.f_small = pygame.font.Font(None, max(16, int(h * 0.034)))

    def capture(self, on):
        pygame.mouse.set_visible(not on)
        pygame.event.set_grab(on)
        try:
            pygame.mouse.get_rel()
        except Exception:
            pass

    def set_state(self, s):
        self.state = s
        self.capture(s in ("play", "read"))
        self.audio.ambient(s in ("play", "read", "pause"))

    def set_message(self, text, seconds=4.0):
        self.message = text
        self.message_t = seconds

    def text(self, surf, txt, font, color, pos, center=False, shadow=True):
        img = font.render(txt, True, color)
        r = img.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        if shadow:
            sh = font.render(txt, True, (0, 0, 0))
            surf.blit(sh, (r.x + 2, r.y + 2))
        surf.blit(img, r)
        return r

    # --------------------------------------------------------------- qualidade
    def set_quality(self, qi):
        self.qi = qi % len(QUALITY)
        sw, sh = self.screen.get_size()
        self.aspect = max(1.0, min(2.4, sw / float(max(1, sh))))
        self.RH = QUALITY[self.qi][1]
        self.RW = int(self.RH * self.aspect) // 2 * 2
        self.view = pygame.Surface((self.RW, self.RH))
        # FOV ajustável (valor em graus na horizontal, referência 16:9); janela larga mostra mais dos lados
        vhalf = math.atan(math.tan(math.radians(self.fov / 2.0)) / (16.0 / 9.0))
        self.PROJ = (self.RH / 2.0) / math.tan(vhalf)
        self.ray_c, self.ray_s = [], []
        for sx in range(self.RW):
            a = math.atan((sx + 0.5 - self.RW / 2.0) / self.PROJ)
            self.ray_c.append(math.cos(a))
            self.ray_s.append(math.sin(a))
        self.zbuf = [MAXD] * self.RW
        self.colcache = {}
        self.vig = textures.make_vignette(self.RW, self.RH)
        self.overlay = pygame.Surface((self.RW, self.RH))
        if hasattr(self, "theme_name"):
            self.bg = textures.make_background(self.theme_name, self.RW, self.RH, self.PROJ)

    def change_fov(self, delta):
        self.fov = max(60, min(120, self.fov + delta))
        self.set_quality(self.qi)
        if self.state == "play":
            self.set_message("Campo de visão (FOV): %d°" % self.fov, 2.0)

    # ---------------------------------------------------------------- capítulos
    def load_level(self, i, keep_sanity=True):
        self.lv = i
        L = LEVELS[i]
        self.L = L
        self.grid = [list(r) for r in L["grid"]]
        self.gh = len(self.grid)
        self.gw = len(self.grid[0])
        self.theme_name = L["theme"]
        self.theme = textures.THEMES[self.theme_name]
        self.tex = textures.build(self.theme_name)
        self.colcache = {}
        self.bg = textures.make_background(self.theme_name, self.RW, self.RH, self.PROJ)
        x, y, a = L["start"]
        self.x, self.y, self.angle = x, y, a
        self.z = 0.0
        self.vz = 0.0
        self.on_ground = True
        self.look = 0.0
        self.bob = 0.0
        self.walk = 0.0
        self.step_i = 0
        self.stamina = 100.0
        self.exhausted = False
        self.jump_buf = 0.0
        self.flash = 0.0
        self.last_safe = (x, y)
        self.fall_t = 0.0
        self.items = []
        for (ix, iy, title, text) in L["memories"]:
            self.items.append(dict(kind="memory", x=ix, y=iy, title=title, text=text, taken=False, ph=ix))
        for (ix, iy, title, text) in L["keys"]:
            self.items.append(dict(kind="key", x=ix, y=iy, title=title, text=text, taken=False, ph=iy))
        for (ix, iy, title, text) in L["notes"]:
            self.items.append(dict(kind="note", x=ix, y=iy, title=title, text=text, taken=False, ph=ix + iy))
        for (ix, iy, color, label) in L["switches"]:
            self.items.append(dict(kind="switch", x=ix, y=iy, color=color, title=label, taken=False,
                                   pressed=False, ph=ix))
        for it in self.items:
            it["floor"] = max(0.0, BH.get(self.cell(it["x"], it["y"]), 0.0))
        self.mem_total = len(L["memories"])
        self.mem_found = 0
        self.has_key = False
        self.exit_open = self.mem_total == 0
        self.switch_seq = []
        self.puzzle_done = not L["switches"]
        self.doors = [(x + 0.5, y + 0.5) for y, r in enumerate(self.grid) for x, c in enumerate(r) if c == "D"]
        self.enemy = None
        if L["enemy"]:
            e = L["enemy"]
            sp = e["spawns"][0]
            self.enemy = dict(x=sp[0], y=sp[1], speed=e["speed"], delay=e["delay"], spawns=e["spawns"],
                              seen=False, announced=False)
        self.whisper_t = self.rand.uniform(25, 40)
        self.target = None
        self.set_message(CHAPTERS[i]["intro"] + "  " + L["objective"], 7.0)

    # ------------------------------------------------------------------- mundo
    def cell(self, x, y):
        ix, iy = int(math.floor(x)), int(math.floor(y))
        if ix < 0 or iy < 0 or ix >= self.gw or iy >= self.gh:
            return "#"
        return self.grid[iy][ix]

    def blocked(self, x, y, z):
        r = 0.2
        for cx, cy in ((x - r, y - r), (x + r, y - r), (x - r, y + r), (x + r, y + r)):
            t = self.cell(cx, cy)
            if t in FULL:
                return True
            if z < -0.25 and t != "o":
                return True
            h = BH.get(t)
            if h is not None and h > z + STEP:
                return True
        return False

    def floor_h(self, x, y):
        r = 0.2
        best = -99.0
        for cx, cy in ((x - r, y - r), (x + r, y - r), (x - r, y + r), (x + r, y + r)):
            t = self.cell(cx, cy)
            if t == "o" or t in FULL:
                continue
            h = BH.get(t, 0.0)
            if h > best:
                best = h
        return best

    def los(self, x0, y0, x1, y1):
        d = math.hypot(x1 - x0, y1 - y0)
        n = int(d / 0.15) + 1
        for i in range(1, n):
            t = i / float(n)
            if self.cell(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) in FULL:
                return False
        return True

    # ------------------------------------------------------------------ interação
    def find_target(self):
        best, bd = None, 99.0
        for it in self.items:
            if it["taken"]:
                continue
            d = math.hypot(it["x"] - self.x, it["y"] - self.y)
            if d < 1.15 and abs(it["floor"] - self.z) < 0.9 and d < bd and \
                    self.los(self.x, self.y, it["x"], it["y"]):
                best, bd = ("item", it), d
        for (dx, dy) in self.doors:
            d = math.hypot(dx - self.x, dy - self.y)
            if d < 1.45 and d < bd:
                a = math.atan2(dy - self.y, dx - self.x) - self.angle
                a = (a + math.pi) % (2 * math.pi) - math.pi
                if abs(a) < 1.0:
                    best, bd = ("door", (dx, dy)), d
        return best

    def target_label(self):
        t = self.target
        if not t:
            return ""
        if t[0] == "door":
            return "E  abrir porta" if self.has_key else "E  examinar porta"
        k = t[1]["kind"]
        return {"memory": "E  recolher lembrança", "note": "E  ler", "key": "E  pegar chave",
                "switch": "E  acionar"}[k]

    def interact(self):
        t = self.find_target()
        if not t:
            self.set_message("O silêncio responde. Não há nada ao alcance.", 2.5)
            return
        if t[0] == "door":
            if self.has_key:
                dx, dy = t[1]
                self.grid[int(dy)][int(dx)] = "."
                self.doors.remove(t[1])
                self.audio.play("door")
                self.set_message("A porta cede com um rangido longo.", 3.0)
            else:
                self.audio.play("wrong", 0.6)
                self.set_message("Trancada. Alguma chave deve estar por perto.", 3.0)
            return
        it = t[1]
        if it["kind"] == "note":
            self.open_read(it["title"], it["text"])
            self.audio.play("click", 0.6)
        elif it["kind"] == "key":
            it["taken"] = True
            self.has_key = True
            self.audio.play("pick")
            self.open_read(it["title"], it["text"])
        elif it["kind"] == "memory":
            it["taken"] = True
            self.mem_found += 1
            self.total_memories += 1
            self.sanity = max(10.0, self.sanity - 3)
            self.audio.play("pick")
            self.open_read(it["title"], it["text"])
            if self.mem_found == self.mem_total:
                self.exit_open = True
                self.pending_open = True
        elif it["kind"] == "switch":
            self.press_switch(it)

    def press_switch(self, it):
        if self.puzzle_done:
            return
        order = self.L["switch_order"]
        if it["pressed"]:
            self.set_message("Já está aceso.", 1.5)
            return
        if it["color"] == order[len(self.switch_seq)]:
            it["pressed"] = True
            self.switch_seq.append(it["color"])
            self.audio.play("click")
            if len(self.switch_seq) == len(order):
                self.puzzle_done = True
                for y in range(self.gh):
                    for x in range(self.gw):
                        if self.grid[y][x] == "G":
                            self.grid[y][x] = "."
                self.audio.play("open")
                self.set_message("Todas as luzes acesas. Um portão se abre ao longe.", 5.0)
            else:
                self.set_message("%s aceso (%d/%d)." % (it["title"].capitalize(), len(self.switch_seq), len(order)), 3.0)
        else:
            for s in self.items:
                if s["kind"] == "switch":
                    s["pressed"] = False
            self.switch_seq = []
            self.sanity = max(5.0, self.sanity - 6)
            self.flash = 0.6
            self.audio.play("wrong")
            self.set_message("Estalo. As luzes se apagam: ordem errada.", 3.5)

    def open_read(self, title, text):
        self.read_title, self.read_text, self.read_t = title, text, 0.0
        self.set_state("read")

    def close_read(self):
        self.set_state("play")
        if getattr(self, "pending_open", False):
            self.pending_open = False
            self.audio.play("open", 0.7)
            self.set_message("As três lembranças se juntam. Algo se abre: encontre a saída luminosa.", 6.0)

    # ------------------------------------------------------------------ jogador
    def respawn(self, why):
        self.x, self.y = self.last_safe
        self.z = max(0.0, self.floor_h(self.x, self.y))
        self.vz = 0.0
        self.on_ground = True
        self.deaths += 1
        self.set_message(why, 4.0)

    def update_player(self, dt):
        keys = pygame.key.get_pressed()
        self.angle += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 2.2 * dt
        self.look += (keys[pygame.K_UP] - keys[pygame.K_DOWN]) * 1.1 * dt
        self.look = max(-0.42, min(0.42, self.look))
        fwd = keys[pygame.K_w] - keys[pygame.K_s]
        strafe = keys[pygame.K_d] - keys[pygame.K_a]
        moving = bool(fwd or strafe)
        want_run = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and moving
        sprint = bool(want_run and self.stamina > 1 and not self.exhausted)
        if sprint:
            self.stamina = max(0.0, self.stamina - 28 * dt)
            if self.stamina <= 0:
                self.exhausted = True
        else:
            self.stamina = min(100.0, self.stamina + 16 * dt)
            if self.stamina > 30:
                self.exhausted = False
        speed = RUN if sprint else WALK
        if self.exhausted:
            speed = WALK * 0.8
        if moving:
            n = math.hypot(fwd, strafe)
            ca, sa = math.cos(self.angle), math.sin(self.angle)
            vx = (ca * fwd - sa * strafe) / n * speed
            vy = (sa * fwd + ca * strafe) / n * speed
            nx = self.x + vx * dt
            if not self.blocked(nx, self.y, self.z):
                self.x = nx
            ny = self.y + vy * dt
            if not self.blocked(self.x, ny, self.z):
                self.y = ny
        # pulo
        self.jump_buf = max(0.0, self.jump_buf - dt)
        if self.jump_buf > 0 and self.on_ground and self.stamina > 8:
            self.vz = JUMP_V
            self.on_ground = False
            self.jump_buf = 0.0
            self.stamina -= 6
            self.audio.play("jump", 0.8)
        # vertical
        fh = self.floor_h(self.x, self.y)
        if self.on_ground:
            if fh < self.z - 0.02:
                self.on_ground = False
                self.vz = 0.0
            else:
                self.z = fh
        if not self.on_ground:
            self.vz -= GRAV * dt
            self.z += self.vz * dt
            if self.z <= fh and fh > -50:
                if self.vz < -3.5:
                    self.audio.play("land", 0.9)
                self.z = fh
                self.vz = 0.0
                self.on_ground = True
            elif fh < -50 and self.z < -0.3:
                self.fall_t += dt
                if self.fall_t < dt * 1.5:
                    self.audio.play("fall", 0.8)
                if self.z < -3.5:
                    self.fall_t = 0.0
                    self.sanity = max(5.0, self.sanity - 5)
                    self.flash = 0.8
                    self.respawn("Você cai no vazio e acorda no último lugar firme.")
        if self.on_ground:
            self.fall_t = 0.0
            c = self.cell(self.x, self.y)
            if c in (".", "c", "T"):
                self.last_safe = (math.floor(self.x) + 0.5, math.floor(self.y) + 0.5)
        # balanço da câmera
        if moving and self.on_ground:
            self.walk += dt * (11.0 if sprint else 8.0)
            self.bob = math.sin(self.walk) * (0.03 if sprint else 0.02)
            si = int(self.walk / math.pi)
            if si != self.step_i:
                self.step_i = si
                self.audio.play("step", 0.5)
        else:
            self.bob *= 0.85

    def update_enemy(self, dt):
        e = self.enemy
        if not e:
            return
        if e["delay"] > 0:
            e["delay"] -= dt
            if e["delay"] <= 0 and not e["announced"]:
                e["announced"] = True
                e["x"], e["y"] = self.far_spawn()
                self.set_message("Algo se move nas sombras. Não desvie o olhar.", 4.0)
            return
        dx, dy = self.x - e["x"], self.y - e["y"]
        d = math.hypot(dx, dy)
        a = math.atan2(-dy, -dx) - self.angle
        a = (a + math.pi) % (2 * math.pi) - math.pi
        e["seen"] = d < 16 and abs(a) < 0.78 and self.los(self.x, self.y, e["x"], e["y"])
        if e["seen"]:
            if d < 6:
                self.sanity = max(0.0, self.sanity - (6 - d) * 1.5 * dt)
        else:
            if d > 0.01:
                sp = e["speed"] * dt
                nx, ny = e["x"] + dx / d * sp, e["y"] + dy / d * sp
                if self.cell(nx, e["y"]) not in FULL:
                    e["x"] = nx
                if self.cell(e["x"], ny) not in FULL:
                    e["y"] = ny
        if d < 0.6:
            self.sanity = max(5.0, self.sanity - 14)
            self.flash = 1.0
            self.audio.play("scare")
            e["x"], e["y"] = self.far_spawn()
            e["delay"] = 6.0
            e["announced"] = True
            self.respawn("A sombra te alcança. Você desperta um pouco antes.")

    def far_spawn(self):
        e = self.enemy
        best, bd = e["spawns"][0], -1
        px, py = self.last_safe
        for sp in e["spawns"]:
            d = math.hypot(sp[0] - px, sp[1] - py)
            if d > bd:
                best, bd = sp, d
        return best

    def update_play(self, dt):
        self.t += dt
        self.update_player(dt)
        self.update_enemy(dt)
        self.target = self.find_target()
        self.message_t = max(0.0, self.message_t - dt)
        self.flash = max(0.0, self.flash - dt * 1.3)
        calm = not (self.enemy and self.enemy["seen"])
        if calm:
            self.sanity = min(100.0, self.sanity + 1.4 * dt)
        self.flick = 1 if self.rand.random() < (0.03 if self.sanity > 40 else 0.12) else 0
        self.whisper_t -= dt
        if self.whisper_t <= 0:
            self.whisper_t = self.rand.uniform(22, 38)
            if self.sanity < 70:
                self.set_message(self.rand.choice(WHISPERS), 3.5)
        if self.sanity <= 0.5:
            self.sanity = 35.0
            self.flash = 1.0
            self.audio.play("scare")
            self.respawn("Tudo apaga por um instante. Você volta a si no último lugar firme.")
        # saída
        if self.exit_open:
            for y in range(self.gh):
                for x in range(self.gw):
                    if self.grid[y][x] == "X" and math.hypot(x + 0.5 - self.x, y + 0.5 - self.y) < 1.0:
                        self.finish_level()
                        return
        # qualidade automática
        self.fps_acc += dt
        self.fps_n += 1
        if self.fps_acc >= 2.5:
            self.fps_now = self.fps_n / self.fps_acc
            if self.auto_quality and self.fps_now < 23 and self.qi > 0:
                self.set_quality(self.qi - 1)
                self.set_message("Qualidade reduzida automaticamente para %s (F1 muda)." % QUALITY_NAMES[self.qi], 4.0)
            self.fps_acc = 0.0
            self.fps_n = 0

    def finish_level(self):
        self.audio.play("open")
        if self.lv < len(LEVELS) - 1:
            lines = CHAPTERS[self.lv]["outro"]
            self.start_pages("FIM DO CAPÍTULO %d" % (self.lv + 1), lines, "next")
        else:
            self.ending_key = "good" if self.sanity >= 50 else "bad"
            e = ENDINGS[self.ending_key]
            self.start_pages(e["title"], e["lines"], "end")

    def start_pages(self, title, lines, then):
        self.page_title = title
        self.page_lines = list(lines)
        self.page_t = 0.0
        self.page_done = then
        self.set_state("pages")

    # ------------------------------------------------------------------ render 3D
    def draw_col(self, key, var, tx, y0, y1, sx):
        RH = self.RH
        h = y1 - y0
        if h <= 0 or y1 <= 0 or y0 >= RH:
            return
        surf = self.tex[key][var]
        if y0 >= 0 and y1 <= RH:
            ck = (key, var, tx)
            col = self.colcache.get(ck)
            if col is None:
                col = surf.subsurface((tx, 0, 1, TS))
                self.colcache[ck] = col
            self.view.blit(pygame.transform.scale(col, (1, h)), (sx, y0))
        else:
            vt = max(y0, 0)
            vb = min(y1, RH)
            r0 = int((vt - y0) * TS / float(h))
            r1 = int((vb - y0) * TS / float(h)) + 1
            r0 = min(r0, TS - 1)
            r1 = min(TS, max(r1, r0 + 1))
            sub = surf.subsurface((tx, r0, 1, r1 - r0))
            self.view.blit(pygame.transform.scale(sub, (1, vb - vt)), (sx, vt))

    def render_world(self):
        RW, RH, P = self.RW, self.RH, self.PROJ
        view = self.view
        cam = self.z + EYE + self.bob
        hor = int(RH * 0.5 + self.look * RH + self.bob * RH * 0.8)
        view.blit(self.bg, (0, hor - int(1.5 * RH)))
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        grid, gh, gw = self.grid, self.gh, self.gw
        px, py = self.x, self.y
        rc, rs = self.ray_c, self.ray_s
        zbuf = self.zbuf
        th = self.theme
        exit_open = self.exit_open
        flick = self.flick
        for sx in range(RW):
            c0, s0 = rc[sx], rs[sx]
            dx = ca * c0 - sa * s0
            dy = sa * c0 + ca * s0
            if abs(dx) < 1e-9:
                dx = 1e-9
            if abs(dy) < 1e-9:
                dy = 1e-9
            mx, my = int(px), int(py)
            ddx, ddy = abs(1.0 / dx), abs(1.0 / dy)
            if dx < 0:
                stx, sdx = -1, (px - mx) * ddx
            else:
                stx, sdx = 1, (mx + 1.0 - px) * ddx
            if dy < 0:
                sty, sdy = -1, (py - my) * ddy
            else:
                sty, sdy = 1, (my + 1.0 - py) * ddy
            hits = []
            pend = None
            while True:
                if sdx < sdy:
                    t = sdx
                    sdx += ddx
                    mx += stx
                    side = 0
                else:
                    t = sdy
                    sdy += ddy
                    my += sty
                    side = 1
                if pend is not None:
                    hits.append(pend + (t,))
                    pend = None
                if t > MAXD:
                    break
                if mx < 0 or my < 0 or mx >= gw or my >= gh:
                    hits.append(("#", t, side, mx, my, t))
                    break
                tile = grid[my][mx]
                if tile == ".":
                    continue
                if tile in FULL:
                    hits.append((tile, t, side, mx, my, t))
                    break
                pend = (tile, t, side, mx, my)
            zb = MAXD
            for tile, t, side, hx, hy, te in reversed(hits):
                d = t * c0
                if d < 0.04:
                    d = 0.04
                inv = P / d
                if tile == "o":
                    ya = int(hor + cam * P / max(0.04, te * c0))
                    yb = int(hor + cam * inv)
                    if yb > ya:
                        view.fill(th["pit"], (sx, ya, 1, yb - ya))
                        view.fill(th["lip"], (sx, yb - 1, 1, 1))
                    continue
                lvl = int(d / SHADE_DIST * SHADES)
                if lvl >= SHADES - 1:
                    lvl = SHADES - 1
                else:
                    lvl = min(SHADES - 1, lvl + flick)
                key = tile
                if tile == "X" and exit_open:
                    key = "x"
                    lvl = min(lvl, 2)
                var = lvl * 2 + side
                if wx_is_x(side):
                    wallx = py + t * dy
                else:
                    wallx = px + t * dx
                wallx -= math.floor(wallx)
                tx = int(wallx * TS)
                if (side == 0 and dx > 0) or (side == 1 and dy < 0):
                    tx = TS - 1 - tx
                if tx < 0:
                    tx = 0
                elif tx > TS - 1:
                    tx = TS - 1
                if tile in FULL:
                    y0 = int(hor - (WALL_H - cam) * inv)
                    y1 = int(hor + cam * inv)
                    self.draw_col(key, var, tx, y0, y1, sx)
                    if d < zb:
                        zb = d
                else:
                    bh = BH[tile]
                    y0 = int(hor - (bh - cam) * inv)
                    y1 = int(hor + cam * inv)
                    self.draw_col(key, var, tx, y0, y1, sx)
                    if cam > bh:
                        ya = int(hor + (cam - bh) * P / max(0.04, te * c0))
                        if y0 > ya:
                            base = th["top_crate"] if tile == "c" else th["top_tall"]
                            f = max(0.12, (1.0 - lvl / float(SHADES)) ** 1.35)
                            tint = th["tint"]
                            col = (int(base[0] * f * tint[0]), int(base[1] * f * tint[1]), int(base[2] * f * tint[2]))
                            view.fill(col, (sx, ya, 1, y0 - ya))
                    if tile == "T" and d < zb:
                        zb = d
            zbuf[sx] = zb
        self.render_sprites(cam, hor)
        # pós-processamento
        view.blit(self.vig, (0, 0))
        if self.sanity < 45:
            view.blit(self.vig, (0, 0))
            self.glitch()
        if self.flash > 0:
            self.overlay.fill((235, 235, 245) if self.flash > 0.7 else (150, 20, 20))
            self.overlay.set_alpha(int(150 * min(1.0, self.flash)))
            view.blit(self.overlay, (0, 0))
        elif self.sanity < 35:
            self.overlay.fill((110, 0, 0))
            self.overlay.set_alpha(int((35 - self.sanity) * 1.6))
            view.blit(self.overlay, (0, 0))

    def glitch(self):
        if self.rand.random() < 0.35 + (45 - self.sanity) * 0.01:
            RW, RH = self.RW, self.RH
            y = self.rand.randint(0, RH - 6)
            h = self.rand.randint(2, 6)
            strip = self.view.subsurface((0, y, RW, h)).copy()
            self.view.blit(strip, (self.rand.randint(-6, 6), y))

    def project(self, wx, wy):
        dx, dy = wx - self.x, wy - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.05:
            return None
        a = math.atan2(dy, dx) - self.angle
        a = (a + math.pi) % (2 * math.pi) - math.pi
        if abs(a) > 1.2:
            return None
        depth = dist * math.cos(a)
        if depth < 0.12:
            return None
        return self.RW / 2.0 + math.tan(a) * self.PROJ, depth

    def render_sprites(self, cam, hor):
        P = self.PROJ
        view = self.view
        RW = self.RW
        draw = []
        for it in self.items:
            if it["taken"]:
                continue
            pr = self.project(it["x"], it["y"])
            if pr:
                draw.append((pr[1], pr[0], it))
        e = self.enemy
        if e and e["delay"] <= 0:
            pr = self.project(e["x"], e["y"])
            if pr:
                draw.append((pr[1], pr[0], None))
        draw.sort(key=lambda s: -s[0])
        for depth, sx, it in draw:
            col = int(sx)
            if 0 <= col < RW and depth > self.zbuf[col] + 0.15:
                continue
            if col < -80 or col > RW + 80:
                continue
            f = max(0.28, 1.0 - depth / 13.0)
            if it is None:
                self.draw_enemy(sx, depth, cam, hor, f)
                continue
            k = it["kind"]
            bobv = math.sin(self.t * 2.0 + it["ph"]) * 0.04
            if k == "switch":
                top = int(hor + (cam - (it["floor"] + 0.75)) * P / depth)
                bot = int(hor + (cam - it["floor"]) * P / depth)
                w = max(2, int(P * 0.16 / depth))
                col_on = SWITCH_COLORS[it["color"]]
                lamp = col_on if it["pressed"] else tuple(int(c * 0.30) for c in col_on)
                pygame.draw.rect(view, (int(36 * f), int(36 * f), int(40 * f)), (int(sx - w), top, w * 2, max(1, bot - top)))
                pygame.draw.rect(view, (6, 6, 8), (int(sx - w), top, w * 2, max(1, bot - top)), 1)
                pygame.draw.circle(view, tuple(int(c * (1.0 if it["pressed"] else max(0.6, f))) for c in lamp),
                                   (int(sx), top + w), max(2, w))
                continue
            zc = it["floor"] + 0.46 + bobv
            sy = hor + (cam - zc) * P / depth
            s = max(2.0, P * 0.10 / depth)
            sxi, syi = int(sx), int(sy)
            if k == "memory":
                gold = (int(235 * f), int(190 * f), int(95 * f))
                halo = (int(70 * f), int(52 * f), int(26 * f))
                pygame.draw.circle(view, halo, (sxi, syi), int(s * 1.9))
                pygame.draw.polygon(view, gold, [(sxi, syi - s * 1.3), (sxi + s * 0.9, syi), (sxi, syi + s * 1.3), (sxi - s * 0.9, syi)])
                pygame.draw.circle(view, (int(255 * f), int(246 * f), int(210 * f)), (sxi, syi), max(1, int(s * 0.3)))
            elif k == "note":
                w, h = int(s * 1.5), int(s * 1.1)
                pygame.draw.rect(view, (int(232 * f), int(224 * f), int(196 * f)), (sxi - w // 2, syi - h // 2, w, h))
                pygame.draw.rect(view, (int(70 * f), int(60 * f), int(50 * f)), (sxi - w // 2, syi - h // 2, w, h), 1)
                if h > 6:
                    pygame.draw.line(view, (int(90 * f), int(80 * f), int(70 * f)), (sxi - w // 3, syi - 1), (sxi + w // 3, syi - 1))
            elif k == "key":
                cyan = (int(110 * f), int(220 * f), int(235 * f))
                pygame.draw.circle(view, (int(25 * f), int(60 * f), int(70 * f)), (sxi, syi), int(s * 1.8))
                pygame.draw.circle(view, cyan, (sxi - int(s * 0.5), syi), max(2, int(s * 0.6)), max(1, int(s * 0.25)))
                pygame.draw.line(view, cyan, (sxi, syi), (sxi + int(s * 1.1), syi), max(1, int(s * 0.25)))
                pygame.draw.line(view, cyan, (sxi + int(s * 0.8), syi), (sxi + int(s * 0.8), syi + int(s * 0.5)), 1)

    def draw_enemy(self, sx, depth, cam, hor, f):
        P = self.PROJ
        view = self.view
        top = int(hor + (cam - 1.35) * P / depth)
        bot = int(hor + cam * P / depth)
        w = max(3, int(P * 0.34 / depth))
        jit = self.rand.randint(-1, 1) if self.sanity < 60 else 0
        x = int(sx) + jit
        body = (int(8 * f) + 4, int(8 * f) + 4, int(12 * f) + 6)
        pygame.draw.polygon(view, body, [(x - w // 2, top + (bot - top) // 4), (x + w // 2, top + (bot - top) // 4),
                                         (x + w, bot), (x - w, bot)])
        hr = max(2, w // 2)
        pygame.draw.circle(view, body, (x, top + hr), hr)
        pygame.draw.circle(view, (40, 40, 52), (x, top + hr), hr, 1)
        if depth < 9 and hr >= 2:
            ey = top + hr - 1
            pygame.draw.rect(view, (235, 235, 225), (x - hr // 2 - 1, ey, max(1, hr // 3), max(1, hr // 4)))
            pygame.draw.rect(view, (235, 235, 225), (x + hr // 2, ey, max(1, hr // 3), max(1, hr // 4)))

    # --------------------------------------------------------------------- HUD
    def blit_view(self):
        sw, sh = self.screen.get_size()
        s = min(sw / float(self.RW), sh / float(self.RH))
        size = (max(1, int(self.RW * s)), max(1, int(self.RH * s)))
        if self.scaled is None or self.scaled.get_size() != size:
            self.scaled = pygame.Surface(size)
        pygame.transform.scale(self.view, size, self.scaled)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.scaled, ((sw - size[0]) // 2, (sh - size[1]) // 2))

    def bar(self, x, y, w, h, frac, color, label):
        scr = self.screen
        frac = max(0.0, min(1.0, frac))
        self.text(scr, label, self.f_small, (176, 172, 164), (x, y))
        by = y + self.f_small.get_height() + 1
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 150), (0, 0, w, h), border_radius=h // 2)
        scr.blit(bg, (x, by))
        fw = int(w * frac)
        if fw >= h:
            pygame.draw.rect(scr, color, (x, by, fw, h), border_radius=h // 2)
        elif fw > 1:
            pygame.draw.rect(scr, color, (x, by, max(fw, 3), h), border_radius=h // 2)
        pygame.draw.rect(scr, (96, 96, 102), (x, by, w, h), 1, border_radius=h // 2)

    def draw_hud(self):
        scr = self.screen
        sw, sh = scr.get_size()
        m = int(sh * 0.025)
        self.text(scr, self.L["name"], self.f_mid, (222, 214, 196), (m, m))
        y = m + self.f_mid.get_height() + 2
        self.text(scr, "LEMBRANÇAS", self.f_small, (200, 180, 140), (m, y))
        bx = m + self.f_small.size("LEMBRANÇAS ")[0]
        for i in range(self.mem_total):
            c = (235, 190, 95) if i < self.mem_found else (60, 56, 50)
            pygame.draw.rect(scr, (8, 8, 8), (bx + i * 24 - 1, y - 1, 20, 18))
            pygame.draw.rect(scr, c, (bx + i * 24, y, 18, 16))
        y += self.f_small.get_height() + 4
        extras = []
        if self.L["keys"]:
            extras.append("CHAVE: " + ("sim" if self.has_key else "não"))
        if self.L["switches"]:
            extras.append("LUZES: %d/%d" % (len(self.switch_seq), len(self.L["switch_order"])))
        if extras:
            self.text(scr, "   ".join(extras), self.f_small, (150, 210, 220), (m, y))
        # barras (canto inferior esquerdo)
        bw, bh = int(sw * 0.17), max(8, int(sh * 0.016))
        block = self.f_small.get_height() + 1 + bh
        y2 = sh - m - block
        y1 = y2 - block - int(sh * 0.012)
        if self.exhausted:
            sc = (214, 140, 80)
        else:
            sc = (112, 204, 144)
        if self.sanity < 35:
            pulse = 0.75 + 0.25 * math.sin(self.t * 6.0)
            nc = (int(220 * pulse), int(60 * pulse), int(70 * pulse))
        elif self.sanity < 60:
            nc = (214, 170, 110)
        else:
            nc = (150, 190, 232)
        self.bar(m, y1, bw, bh, self.stamina / 100.0, sc, "FÔLEGO")
        self.bar(m, y2, bw, bh, self.sanity / 100.0, nc, "SANIDADE")
        # mira
        pygame.draw.circle(scr, (225, 225, 215), (sw // 2, sh // 2), 2)
        # prompt
        label = self.target_label()
        if label:
            self.text(scr, label, self.f_mid, (245, 230, 180), (sw // 2, int(sh * 0.62)), center=True)
        # mensagem
        if self.message_t > 0 and self.message:
            lines = wrap(self.message, self.f_small, int(sw * 0.7))
            lh = self.f_small.get_height() + 2
            bw = max(self.f_small.size(l)[0] for l in lines) + 28
            bh = lh * len(lines) + 16
            bx2, by2 = (sw - bw) // 2, int(sh * 0.76)
            box = pygame.Surface((bw, bh))
            box.set_alpha(170)
            box.fill((0, 0, 0))
            scr.blit(box, (bx2, by2))
            for i, l in enumerate(lines):
                self.text(scr, l, self.f_small, (236, 232, 220), (bx2 + 14, by2 + 8 + i * lh), shadow=False)
        if self.show_help:
            hint = "WASD mover  |  MOUSE olhar (cima/baixo também)  |  ESPAÇO pular  |  SHIFT correr  |  E interagir  |  -/+ FOV  |  ESC pausa  |  H ocultar"
            self.text(scr, hint, self.f_small, (150, 150, 146), (sw // 2, 8 + self.f_small.get_height() // 2), center=True)
        if self.show_fps:
            self.text(scr, "%d FPS  %dx%d (%s)" % (self.fps_now, self.RW, self.RH, QUALITY_NAMES[self.qi]), self.f_small,
                      (140, 220, 140), (sw - 260, int(sh * 0.06)))

    def draw_panel(self, title, body, t):
        scr = self.screen
        sw, sh = scr.get_size()
        shade = pygame.Surface((sw, sh))
        shade.set_alpha(150)
        shade.fill((0, 0, 0))
        scr.blit(shade, (0, 0))
        pw, ph = int(sw * 0.72), int(sh * 0.56)
        px, py = (sw - pw) // 2, int(sh * 0.2)
        pygame.draw.rect(scr, (26, 22, 19), (px, py, pw, ph))
        pygame.draw.rect(scr, (130, 108, 74), (px, py, pw, ph), 2)
        self.text(scr, title, self.f_big, (232, 196, 120), (px + 24, py + 18))
        shown = body[:int(t * 55)]
        y = py + 24 + self.f_big.get_height()
        for l in wrap(shown, self.f_mid, pw - 48):
            self.text(scr, l, self.f_mid, (228, 222, 208), (px + 24, y), shadow=False)
            y += self.f_mid.get_height() + 4
        if t * 55 >= len(body):
            self.text(scr, "E / ENTER — continuar", self.f_small, (160, 150, 130), (px + 24, py + ph - 30))

    # ------------------------------------------------------------------ telas
    def draw_noise_bg(self):
        scr = self.screen
        sw, sh = scr.get_size()
        scr.fill((4, 5, 8))
        for _ in range(26):
            y = self.rand.randint(0, sh)
            v = self.rand.randint(14, 40)
            pygame.draw.line(scr, (v, v, v + 6), (0, y), (sw, y), self.rand.randint(1, 2))

    def draw_title(self):
        self.draw_noise_bg()
        scr = self.screen
        sw, sh = scr.get_size()
        jit = self.rand.randint(-2, 2) if self.rand.random() < 0.08 else 0
        self.text(scr, "O ÚLTIMO SINAL", self.f_title, (224, 216, 198), (sw // 2 + jit, int(sh * 0.30)), center=True)
        self.text(scr, "EDIÇÃO LEVE 2.0  |  TERROR PSICOLÓGICO", self.f_mid, (150, 150, 146), (sw // 2, int(sh * 0.42)), center=True)
        if int(self.t * 1.6) % 2 == 0:
            self.text(scr, "ENTER — COMEÇAR", self.f_big, (214, 188, 140), (sw // 2, int(sh * 0.60)), center=True)
        lines = ["WASD mover   MOUSE olhar (cima e baixo)   ESPAÇO pular   SHIFT correr   E interagir",
                 "F1 qualidade   - / + campo de visão (FOV)   F3 FPS   M som   F11 tela cheia   ESC pausa"]
        for i, l in enumerate(lines):
            self.text(scr, l, self.f_small, (140, 140, 138), (sw // 2, int(sh * 0.75) + i * (self.f_small.get_height() + 6)), center=True)

    def draw_pages(self):
        self.draw_noise_bg()
        scr = self.screen
        sw, sh = scr.get_size()
        self.text(scr, self.page_title, self.f_big, (224, 196, 130), (sw // 2, int(sh * 0.14)), center=True)
        full = "\n\n".join(self.page_lines)
        shown = full[:int(self.page_t * 42)]
        y = int(sh * 0.26)
        for l in wrap(shown, self.f_mid, int(sw * 0.72)):
            self.text(scr, l, self.f_mid, (220, 214, 200), (int(sw * 0.14), y), shadow=False)
            y += self.f_mid.get_height() + 4
        if self.page_t * 42 >= len(full):
            if self.page_done == "end":
                self.text(scr, "Lembranças reunidas: %d    Quedas e capturas: %d    Sanidade final: %d%%" %
                          (self.total_memories, self.deaths, int(self.sanity)), self.f_small, (160, 200, 160),
                          (sw // 2, int(sh * 0.86)), center=True)
            self.text(scr, "ENTER — continuar", self.f_small, (170, 160, 140), (sw // 2, int(sh * 0.93)), center=True)

    def draw_pause(self):
        scr = self.screen
        sw, sh = scr.get_size()
        shade = pygame.Surface((sw, sh))
        shade.set_alpha(190)
        shade.fill((0, 0, 0))
        scr.blit(shade, (0, 0))
        self.text(scr, "PAUSADO", self.f_title, (224, 216, 198), (sw // 2, int(sh * 0.32)), center=True)
        opts = ["ESC / ENTER  continuar", "R  recomeçar o capítulo", "F1  qualidade: %s (%dx%d)" % (QUALITY_NAMES[self.qi], self.RW, self.RH),
                "SETAS ESQ/DIR  ou  - / +   campo de visão (FOV): %d°" % self.fov,
                "M  som: %s" % ("desligado" if self.audio.muted else "ligado"), "Q  voltar ao título"]
        for i, o in enumerate(opts):
            self.text(scr, o, self.f_mid, (190, 186, 176), (sw // 2, int(sh * 0.50) + i * (self.f_mid.get_height() + 8)), center=True)

    # --------------------------------------------------------------- eventos
    def new_game(self):
        self.sanity = 100.0
        self.deaths = 0
        self.total_memories = 0
        self.load_level(0)
        self.set_state("play")

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.WINDOWFOCUSLOST and self.state == "play":
            self.set_state("pause")
        if ev.type == pygame.MOUSEMOTION and self.state == "play":
            dx = max(-90, min(90, ev.rel[0]))
            dy = max(-90, min(90, ev.rel[1]))
            self.angle += dx * MOUSE_X
            self.look = max(-0.42, min(0.42, self.look - dy * MOUSE_Y))
        if ev.type != pygame.KEYDOWN:
            return True
        k = ev.key
        if k == pygame.K_F1:
            self.auto_quality = False
            self.set_quality(self.qi + 1)
            if self.state == "play":
                self.set_message("Qualidade: %s (%dx%d)" % (QUALITY_NAMES[self.qi], self.RW, self.RH), 2.5)
        elif k == pygame.K_F3:
            self.show_fps = not self.show_fps
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS) and self.state in ("play", "pause"):
            self.change_fov(-5)
        elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS) and self.state in ("play", "pause"):
            self.change_fov(5)
        elif k == pygame.K_LEFT and self.state == "pause":
            self.change_fov(-5)
        elif k == pygame.K_RIGHT and self.state == "pause":
            self.change_fov(5)
        elif k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_m:
            self.audio.toggle_mute()
            self.audio.ambient(self.state in ("play", "read", "pause"))
        elif k == pygame.K_h and self.state == "play":
            self.show_help = not self.show_help
        s = self.state
        if s == "title":
            if k == pygame.K_RETURN:
                self.start_pages("PRÓLOGO", PROLOGUE, "start")
            elif k == pygame.K_ESCAPE:
                return False
        elif s == "pages":
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                full = len("\n\n".join(self.page_lines))
                if self.page_t * 42 < full:
                    self.page_t = full / 42.0 + 0.1
                elif self.page_done == "start":
                    self.new_game()
                elif self.page_done == "next":
                    self.load_level(self.lv + 1)
                    self.set_state("play")
                else:
                    self.set_state("title")
        elif s == "play":
            if k == pygame.K_ESCAPE:
                self.set_state("pause")
            elif k == pygame.K_e:
                self.interact()
            elif k == pygame.K_SPACE:
                self.jump_buf = 0.14
        elif s == "read":
            if k in (pygame.K_e, pygame.K_RETURN, pygame.K_ESCAPE) and self.read_t > 0.25:
                self.close_read()
        elif s == "pause":
            if k in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.set_state("play")
            elif k == pygame.K_r:
                self.total_memories -= self.mem_found
                self.load_level(self.lv)
                self.set_state("play")
            elif k == pygame.K_q:
                self.set_state("title")
        return True

    # --------------------------------------------------------------- laço
    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(40) / 1000.0, 0.05)
            self.screen = pygame.display.get_surface()
            if self.screen.get_height() != self.fonts_h:
                self.build_fonts()
            sw0, sh0 = self.screen.get_size()
            asp = max(1.0, min(2.4, sw0 / float(max(1, sh0))))
            if abs(asp - self.aspect) > 0.03:
                self.set_quality(self.qi)
            for ev in pygame.event.get():
                if not self.handle_event(ev):
                    running = False
            self.t += dt if self.state != "play" else 0.0
            s = self.state
            if s == "play":
                self.update_play(dt)
                if self.state == "play":
                    self.render_world()
                    self.blit_view()
                    self.draw_hud()
            elif s == "read":
                self.read_t += dt
                self.render_world()
                self.blit_view()
                self.draw_hud()
                self.draw_panel(self.read_title, self.read_text, self.read_t)
            elif s == "pause":
                self.blit_view()
                self.draw_hud()
                self.draw_pause()
            elif s == "pages":
                self.page_t += dt
                self.draw_pages()
            else:
                self.draw_title()
            pygame.display.flip()
        pygame.quit()


def wx_is_x(side):
    """Em colisões com faces verticais (side 0) a coordenada da textura vem de y."""
    return side == 0


def main():
    Game().run()
    sys.exit()


if __name__ == "__main__":
    main()