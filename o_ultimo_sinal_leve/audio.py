# Sons gerados por código (sem arquivos). Se não houver áudio, tudo vira silêncio.
import array
import math
import random
import pygame


class Audio:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self.amb = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _fmt, self.channels = pygame.mixer.get_init()
            self.ok = True
            self._build()
        except Exception:
            self.ok = False

    # ------------------------------------------------------------ síntese
    def _snd(self, samples):
        if self.channels == 2:
            st = array.array("h")
            for v in samples:
                st.append(v)
                st.append(v)
            samples = st
        else:
            samples = array.array("h", samples)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _tone(self, f0, f1, dur, vol=0.4, decay=4.0, noise=0.0):
        n = int(self.rate * dur)
        out = []
        ph = 0.0
        for i in range(n):
            t = i / self.rate
            f = f0 + (f1 - f0) * (i / n)
            ph += 2 * math.pi * f / self.rate
            v = math.sin(ph) * (1 - noise) + (random.uniform(-1, 1) * noise)
            v *= math.exp(-t * decay) * vol
            out.append(int(max(-1, min(1, v)) * 32000))
        return out

    def _build(self):
        S = self.sounds
        S["jump"] = self._snd(self._tone(180, 360, 0.16, 0.30, 9))
        S["land"] = self._snd(self._tone(90, 40, 0.18, 0.55, 14, 0.35))
        S["step"] = self._snd(self._tone(70, 50, 0.07, 0.30, 30, 0.7))
        S["pick"] = self._snd(self._tone(660, 990, 0.35, 0.30, 5)
                              + self._tone(990, 1320, 0.35, 0.25, 5))
        S["click"] = self._snd(self._tone(900, 500, 0.06, 0.35, 40, 0.3))
        S["door"] = self._snd(self._tone(70, 45, 0.7, 0.5, 3, 0.4))
        S["fall"] = self._snd(self._tone(500, 60, 0.9, 0.35, 2.2))
        S["scare"] = self._snd(self._tone(300, 40, 0.9, 0.7, 2.5, 0.55))
        S["wrong"] = self._snd(self._tone(220, 110, 0.35, 0.4, 6, 0.2))
        S["open"] = self._snd(self._tone(220, 880, 0.8, 0.35, 2.0))
        # ambiente em loop (frequências inteiras em 4 s => emenda perfeita)
        n = int(self.rate * 4)
        amb = []
        for i in range(n):
            t = i / self.rate
            v = 0.5 * math.sin(2 * math.pi * 55 * t) + 0.5 * math.sin(2 * math.pi * 57.5 * t)
            v += 0.12 * math.sin(2 * math.pi * 110.25 * t + math.sin(2 * math.pi * 0.25 * t) * 3)
            amb.append(int(v * 0.35 * 32000))
        self.amb = self._snd(amb)

    # ---------------------------------------------------------------- uso
    def play(self, name, vol=1.0):
        if not self.ok or self.muted:
            return
        s = self.sounds.get(name)
        if s:
            s.set_volume(vol)
            s.play()

    def ambient(self, on):
        if not self.ok or not self.amb:
            return
        if on and not self.muted:
            self.amb.set_volume(0.35)
            if self.amb.get_num_channels() == 0:
                self.amb.play(loops=-1)
        else:
            self.amb.stop()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.stop()
        return self.muted
