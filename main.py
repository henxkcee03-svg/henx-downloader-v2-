import os
import math
import json
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Triangle, PushMatrix, PopMatrix, Rotate, Translate
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.animation import Animation
from kivy.metrics import dp
import yt_dlp

# ---------- Palette ----------
# ACCENT/ACCENT_2/GOOD/BAD/WARN are the "special" colors — they stay the
# same in both themes (buttons, badges, active toggles). Everything else
# (BG/SURFACE/SURFACE_2/BORDER/TEXT_PRIMARY/TEXT_MUTED) switches between
# a true black/white/grey dark mode and a light mode via apply_palette().
ACCENT = (0.18, 0.65, 1.0, 1)
ACCENT_2 = (0.36, 0.85, 0.75, 1)
GOOD = (0.35, 0.85, 0.55, 1)
BAD = (0.98, 0.42, 0.45, 1)
WARN = (0.98, 0.75, 0.3, 1)

DARK_PALETTE = {
    'BG': (0, 0, 0, 1),
    'SURFACE': (0.09, 0.09, 0.09, 1),
    'SURFACE_2': (0.17, 0.17, 0.17, 1),
    'BORDER': (0.3, 0.3, 0.3, 1),
    'TEXT_PRIMARY': (1, 1, 1, 1),
    'TEXT_MUTED': (0.62, 0.62, 0.62, 1),
}
LIGHT_PALETTE = {
    'BG': (0.91, 0.915, 0.925, 1),
    'SURFACE': (1, 1, 1, 1),
    'SURFACE_2': (0.905, 0.91, 0.925, 1),
    'BORDER': (0.74, 0.75, 0.78, 1),
    'TEXT_PRIMARY': (0.07, 0.08, 0.1, 1),
    'TEXT_MUTED': (0.4, 0.42, 0.47, 1),
}

BG = DARK_PALETTE['BG']
SURFACE = DARK_PALETTE['SURFACE']
SURFACE_2 = DARK_PALETTE['SURFACE_2']
BORDER = DARK_PALETTE['BORDER']
TEXT_PRIMARY = DARK_PALETTE['TEXT_PRIMARY']
TEXT_MUTED = DARK_PALETTE['TEXT_MUTED']


def apply_palette(name):
    """Swaps the module-level neutral colors. Every widget builder reads
    these names fresh at construction time, so rebuilding the screens
    after calling this picks up the new theme automatically."""
    global BG, SURFACE, SURFACE_2, BORDER, TEXT_PRIMARY, TEXT_MUTED
    pal = DARK_PALETTE if name == 'dark' else LIGHT_PALETTE
    BG = pal['BG']
    SURFACE = pal['SURFACE']
    SURFACE_2 = pal['SURFACE_2']
    BORDER = pal['BORDER']
    TEXT_PRIMARY = pal['TEXT_PRIMARY']
    TEXT_MUTED = pal['TEXT_MUTED']
    Window.clearcolor = BG


Window.clearcolor = BG


# ---------- Vector icons ----------
# Drawn on-canvas instead of using unicode glyphs (which have no guaranteed
# font support on Android and were rendering as empty "tofu" boxes). Every
# icon redraws itself on resize and supports a color-fade + a spin, so the
# nav bar and buttons can animate instead of sitting static.

class VectorIcon(Widget):
    def __init__(self, color=None, icon_size=22, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(icon_size), dp(icon_size)), **kwargs)
        self._color = list(color if color else TEXT_MUTED)
        with self.canvas:
            PushMatrix()
            self._rotate = Rotate(angle=0, origin=self.center)
            self._gcolor = Color(*self._color)
            self._build()
            PopMatrix()
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _build(self):
        """Subclasses create their Line/Triangle instructions here."""
        raise NotImplementedError

    def _redraw(self, *args):
        self._rotate.origin = self.center

    def set_color(self, color, animate=True):
        if animate:
            Animation(rgba=list(color), d=0.18, t='out_quad').start(self._gcolor)
        else:
            self._gcolor.rgba = list(color)

    def spin(self, degrees=180, duration=0.4):
        Animation(angle=self._rotate.angle + degrees, d=duration, t='out_cubic').start(self._rotate)

    def bounce(self):
        # A quick playful wiggle built from the same Rotate.angle property
        # spin() uses — a tap "bounce" without touching widget size/layout.
        base = self._rotate.angle
        anim = (Animation(angle=base - 12, d=0.05, t='out_quad')
                + Animation(angle=base + 9, d=0.08, t='in_out_quad')
                + Animation(angle=base, d=0.09, t='out_back'))
        anim.start(self._rotate)


class HomeIcon(VectorIcon):
    def _build(self):
        self._roof = Line(points=[0, 0, 0, 0, 0, 0], width=dp(1.8), joint='round', cap='round')
        self._body = Line(width=dp(1.7))
        self._door = Line(width=dp(1.4))

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y = self.pos
        w, h = self.size
        roof_h = h * 0.42
        self._roof.points = [
            x + w * 0.06, y + h - roof_h,
            x + w * 0.5, y + h - dp(1),
            x + w * 0.94, y + h - roof_h,
        ]
        body_top = y + h - roof_h + dp(1)
        body_y = y + h * 0.08
        self._body.rectangle = (x + w * 0.16, body_y, w * 0.68, body_top - body_y)
        door_w, door_h = w * 0.2, (body_top - body_y) * 0.5
        self._door.rectangle = (x + w / 2 - door_w / 2, body_y, door_w, door_h)


class SettingsIcon(VectorIcon):
    N_TEETH = 8

    def _build(self):
        self._outer = Line(width=dp(1.8))
        self._inner = Line(width=dp(1.6))
        self._teeth = [Line(width=dp(2.0)) for _ in range(self.N_TEETH)]

    def _redraw(self, *args):
        super()._redraw(*args)
        cx, cy = self.center
        w, h = self.size
        r_outer = min(w, h) * 0.30
        r_inner = min(w, h) * 0.13
        self._outer.circle = (cx, cy, r_outer)
        self._inner.circle = (cx, cy, r_inner)
        r1, r2 = r_outer * 1.05, r_outer * 1.42
        for i, tooth in enumerate(self._teeth):
            angle = (2 * math.pi / self.N_TEETH) * i
            ca, sa = math.cos(angle), math.sin(angle)
            tooth.points = [cx + r1 * ca, cy + r1 * sa, cx + r2 * ca, cy + r2 * sa]


class ProfileIcon(VectorIcon):
    def _build(self):
        self._head = Line(width=dp(1.8))
        self._shoulders = Line(width=dp(1.8), cap='round')

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y = self.pos
        w, h = self.size
        head_r = w * 0.185
        head_cx, head_cy = x + w * 0.5, y + h * 0.72
        self._head.circle = (head_cx, head_cy, head_r)
        self._shoulders.ellipse = (x + w * 0.14, y + h * 0.02, w * 0.72, h * 0.62, 180, 360)


class HelpIcon(VectorIcon):
    """A simple question-mark glyph, hand-drawn as a curve + dot to match
    the other icons instead of relying on a font's '?' glyph."""
    def _build(self):
        self._ring = Line(width=dp(1.8))
        self._hook = Line(width=dp(1.9), cap='round', joint='round')
        self._dot = Line(width=dp(2.4), cap='round')

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y = self.pos
        w, h = self.size
        cx = x + w * 0.5
        self._ring.circle = (cx, y + h * 0.5, w * 0.42)
        self._hook.bezier = [
            cx - w * 0.16, y + h * 0.62,
            cx - w * 0.05, y + h * 0.78,
            cx + w * 0.14, y + h * 0.62,
            cx, y + h * 0.44,
        ]
        dot_y = y + h * 0.2
        self._dot.points = [cx, dot_y, cx, dot_y]


class FolderIcon(VectorIcon):
    """A simple folder outline for the Files/Library tab."""
    def _build(self):
        self._tab = Line(width=dp(1.8), joint='round')
        self._body = Line(width=dp(1.8), joint='round')

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y = self.pos
        w, h = self.size
        top = y + h * 0.68
        self._tab.points = [
            x + w * 0.18, top,
            x + w * 0.4, top,
            x + w * 0.48, top + h * 0.1,
            x + w * 0.82, top + h * 0.1,
        ]
        self._body.points = [
            x + w * 0.18, top,
            x + w * 0.14, y + h * 0.2,
            x + w * 0.86, y + h * 0.2,
            x + w * 0.82, top + h * 0.1,
        ]


# ---------- Reusable styled widgets ----------

class Card(BoxLayout):
    def __init__(self, radius=22, bg=SURFACE, border=BORDER, **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        with self.canvas.before:
            # a soft shadow reads much better on light backgrounds than
            # dark ones (on black, a dark shadow is invisible anyway),
            # so only draw it in light mode — gives cards real depth
            # instead of looking like flat grey rectangles.
            if TEXT_PRIMARY[0] < 0.5:  # true when in light mode (dark text)
                Color(0, 0, 0, 0.08)
                self._shadow = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            else:
                self._shadow = None
            Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            Color(*border)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, radius), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        if self._shadow:
            self._shadow.pos = (self.x, self.y - dp(2.5))
            self._shadow.size = self.size
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self._radius)


class GradientButton(Button):
    def __init__(self, c1=ACCENT, text_color=(0.03, 0.05, 0.07, 1), radius=26, show_play_icon=False, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = text_color
        self.bold = True
        self._c1 = c1
        self._radius = radius
        self._show_play_icon = show_play_icon
        with self.canvas.before:
            self._c = Color(*c1)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        if show_play_icon:
            with self.canvas.after:
                self._icon_color = Color(*text_color)
                self._play_tri = Triangle()
            self._start_idle_pulse()
        self.bind(pos=self._update, size=self._update, state=self._on_state)
        self._update()

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        if self._show_play_icon:
            cx = self.x + dp(26)
            cy = self.center_y
            s = dp(8)
            self._play_tri.points = [cx - s * 0.55, cy + s, cx - s * 0.55, cy - s, cx + s * 0.95, cy]

    def _on_state(self, instance, value):
        target = tuple(c * 0.8 for c in self._c1[:3]) + (1,) if value == 'down' else self._c1
        self._c.rgba = target

    def _start_idle_pulse(self):
        pulse = (Animation(a=0.5, d=0.6, t='in_out_sine') + Animation(a=1, d=0.6, t='in_out_sine'))
        pulse.repeat = True
        pulse.start(self._icon_color)


class GhostButton(Button):
    def __init__(self, border=BORDER, radius=24, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = TEXT_PRIMARY
        self.bold = True
        self._radius = radius
        with self.canvas.before:
            Color(*SURFACE_2)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            Color(*border)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, radius), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self._radius)


class RoundedSpinnerOption(SpinnerOption):
    """One row in the dropdown list. Kivy's default option is a plain
    square grey button — this reads the current theme colors so it
    matches dark or light mode instead of always looking like the
    unthemed default."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = TEXT_PRIMARY
        self.font_size = '13sp'
        with self.canvas.before:
            Color(*SURFACE_2)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class RoundedSpinner(Spinner):
    """A Spinner with a true pill-shaped background (radius = half the
    height, so it's fully rounded regardless of size) instead of Kivy's
    default sharp-cornered box."""
    def __init__(self, **kwargs):
        kwargs.setdefault('option_cls', RoundedSpinnerOption)
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = TEXT_PRIMARY
        with self.canvas.before:
            Color(*SURFACE_2)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
            Color(*BORDER)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(18)), width=1.2)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        radius = self.height / 2
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [radius]
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, radius)


class RoundedTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_active = ''
        self.foreground_color = TEXT_PRIMARY
        self.hint_text_color = TEXT_MUTED
        self.cursor_color = ACCENT
        self.padding = [dp(14), dp(14), dp(14), dp(14)]
        with self.canvas.before:
            Color(*SURFACE_2)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
            Color(*BORDER)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 20), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, 20)


class RoundedProgressBar(Widget):
    """Custom progress bar drawn with rounded canvas rectangles, replacing
    Kivy's stock ProgressBar (which renders as a default grey/blocky bar
    that clashed with the rest of the rounded, dark custom UI)."""
    def __init__(self, value=0, max=100, track=SURFACE_2, fill=ACCENT, **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.max = max
        self._fill_color_val = fill
        with self.canvas:
            Color(*track)
            self._track = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            self._fcolor = Color(*fill)
            self._fill = RoundedRectangle(pos=self.pos, size=(0, self.size[1]), radius=[self.height / 2])
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        r = self.height / 2
        self._track.pos = self.pos
        self._track.size = self.size
        self._track.radius = [r]
        pct = 0 if self.max <= 0 else max(0, min(1, self.value / self.max))
        fill_w = max(self.height, self.width * pct) if pct > 0 else 0
        self._fill.pos = self.pos
        self._fill.size = (fill_w, self.height)
        self._fill.radius = [r]

    def set_value(self, value, animate=True):
        self.value = max(0, min(self.max, value))
        if animate:
            pct = 0 if self.max <= 0 else self.value / self.max
            target_w = max(self.height, self.width * pct) if pct > 0 else 0
            Animation(size=(target_w, self.height), d=0.25, t='out_quad').start(self._fill)
        else:
            self._redraw()


class Pill(BoxLayout):
    def __init__(self, text="", bg=SURFACE_2, fg=TEXT_MUTED, **kwargs):
        super().__init__(size_hint=(None, None), height=dp(26), padding=[dp(10), 0], **kwargs)
        self.width = dp(70)
        with self.canvas.before:
            self._c = Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[13])
        self.bind(pos=self._update, size=self._update)
        self.label = Label(text=text, font_size='11sp', bold=True, color=fg)
        self.add_widget(self.label)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set(self, text, bg, fg):
        self.label.text = text
        self.label.color = fg
        self._c.rgba = bg


class SectionLabel(Label):
    def __init__(self, text, **kwargs):
        super().__init__(
            text=text, font_size='12sp', bold=True,
            color=TEXT_MUTED, size_hint_y=None, height=dp(20),
            halign='left', valign='middle', **kwargs
        )
        self.bind(size=self.setter('text_size'))


class ToggleSwitch(BoxLayout):
    TRACK_W, TRACK_H = dp(54), dp(30)
    KNOB = dp(24)
    PAD = dp(3)

    def __init__(self, active=False, on_change=None, **kwargs):
        super().__init__(size_hint=(None, None), size=(self.TRACK_W, self.TRACK_H), **kwargs)
        self.active = active
        self.on_change = on_change
        with self.canvas.before:
            self._bg_color = Color(*(ACCENT if active else SURFACE_2))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.TRACK_H / 2])
        with self.canvas.after:
            self._knob_color = Color(0.88, 0.91, 0.95, 1)
            self._knob = RoundedRectangle(pos=self._knob_pos(), size=(self.KNOB, self.KNOB), radius=[self.KNOB / 2])
        self.bind(pos=self._update, size=self._update)
        self.bind(on_touch_down=self._on_touch)

    def _knob_pos(self):
        if self.active:
            return (self.x + self.width - self.KNOB - self.PAD, self.y + self.PAD)
        return (self.x + self.PAD, self.y + self.PAD)

    def _update(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bg.radius = [self.height / 2]
        self._knob.pos = self._knob_pos()

    def _on_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.active = not self.active
            Animation(rgba=(ACCENT if self.active else SURFACE_2), d=0.16, t='out_quad').start(self._bg_color)
            Animation(pos=self._knob_pos(), d=0.2, t='out_back').start(self._knob)
            if self.on_change:
                self.on_change(self.active)
            return True
        return False


class SettingsRow(BoxLayout):
    """A labeled row inside a settings card: title + optional subtitle on the
    left, an arbitrary control widget on the right."""
    def __init__(self, title, control, subtitle=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=dp(56), spacing=dp(10), **kwargs)
        text_wrap = BoxLayout(orientation='vertical')
        title_lbl = Label(text=title, font_size='14sp', color=TEXT_PRIMARY, bold=True,
                           halign='left', valign='middle', size_hint_y=None, height=dp(20))
        title_lbl.bind(size=title_lbl.setter('text_size'))
        text_wrap.add_widget(title_lbl)
        if subtitle:
            sub_lbl = Label(text=subtitle, font_size='11sp', color=TEXT_MUTED,
                             halign='left', valign='middle', size_hint_y=None, height=dp(16))
            sub_lbl.bind(size=sub_lbl.setter('text_size'))
            text_wrap.add_widget(sub_lbl)
        self.add_widget(text_wrap)
        control_wrap = BoxLayout(size_hint=(None, 1), width=dp(90))
        control_wrap.add_widget(control)
        self.add_widget(control_wrap)


class CheckIcon(VectorIcon):
    def _build(self):
        self._mark = Line(width=dp(2.0), joint='round', cap='round')

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y, w, h = self.x, self.y, self.width, self.height
        self._mark.points = [
            x + w * 0.18, y + h * 0.52,
            x + w * 0.42, y + h * 0.26,
            x + w * 0.85, y + h * 0.72,
        ]


class XIcon(VectorIcon):
    def _build(self):
        self._a = Line(width=dp(2.0), cap='round')
        self._b = Line(width=dp(2.0), cap='round')

    def _redraw(self, *args):
        super()._redraw(*args)
        x, y, w, h = self.x, self.y, self.width, self.height
        pad = w * 0.22
        self._a.points = [x + pad, y + h - pad, x + w - pad, y + pad]
        self._b.points = [x + pad, y + pad, x + w - pad, y + h - pad]


class SummaryBadge(BoxLayout):
    """Replaces the old ✓/✕ text summary with real vector icons next to
    animated counts, so it never renders as empty tofu boxes."""

    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', size_hint=(None, None),
                          height=dp(24), spacing=dp(4), **kwargs)
        self.width = dp(150)
        self._done = 0
        self._fail = 0
        self._total = 0

        self.check_icon = CheckIcon(color=GOOD, icon_size=15)
        self.done_label = Label(text="0", font_size='12sp', bold=True, color=GOOD,
                                 size_hint_x=None, width=dp(18))
        self.x_icon = XIcon(color=BAD, icon_size=15)
        self.fail_label = Label(text="0", font_size='12sp', bold=True, color=BAD,
                                 size_hint_x=None, width=dp(18))
        self.total_label = Label(text="/0", font_size='12sp', bold=True, color=TEXT_MUTED,
                                  size_hint_x=None, width=dp(30))

        for w in (self.check_icon, self.done_label, self.x_icon, self.fail_label, self.total_label):
            self.add_widget(w)

    def _pop(self, label):
        Animation.cancel_all(label, 'font_size')
        base = 12
        (Animation(font_size=base + 4, d=0.08, t='out_quad')
         + Animation(font_size=base, d=0.12, t='out_back')).start(label)

    def update(self, done, fail, total):
        if done != self._done:
            self.done_label.text = str(done)
            self.check_icon.bounce()
            self._pop(self.done_label)
        if fail != self._fail:
            self.fail_label.text = str(fail)
            self.x_icon.bounce()
            self._pop(self.fail_label)
        if total != self._total:
            self.total_label.text = f"/{total}"
        self._done, self._fail, self._total = done, fail, total


class HeaderLogo(Widget):
    """A small hand-drawn download arrow that continuously bobs up and
    down, simulating a download in progress. Replaces the static
    icon.png image in the header — that raster image had a hardcoded
    dark background baked in, so it looked like a stray dark square
    when the app switched to light mode. This is theme-colorable and
    animated instead."""

    def __init__(self, color=ACCENT, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (dp(26), dp(26)))
        super().__init__(**kwargs)
        with self.canvas:
            PushMatrix()
            self._translate = Translate(0, 0)
            Color(*color)
            self._stem = Line(width=dp(2.2), cap='round')
            self._head = Triangle()
            self._tray = Line(width=dp(2.3), cap='round')
            PopMatrix()
        self.bind(pos=self._layout, size=self._layout)
        self._layout()
        Clock.schedule_once(lambda dt: self._loop(), 0.2)

    def _layout(self, *args):
        x, y, w, h = self.x, self.y, self.width, self.height
        cx = x + w / 2
        self._stem.points = [cx, y + h * 0.88, cx, y + h * 0.52]
        half = w * 0.24
        self._head.points = [cx - half, y + h * 0.52, cx + half, y + h * 0.52, cx, y + h * 0.28]
        self._tray.points = [x + w * 0.2, y + h * 0.1, x + w * 0.8, y + h * 0.1]

    def _loop(self):
        down = Animation(y=-dp(4), d=0.55, t='in_out_sine')
        up = Animation(y=0, d=0.55, t='in_out_sine')
        seq = down + up
        seq.repeat = True
        seq.start(self._translate)


class LoadingDots(Widget):
    """Three animated dots for the splash screen, drawn on canvas so they
    render identically on every device regardless of font support."""

    def __init__(self, dot_color=ACCENT, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (dp(64), dp(22)))
        super().__init__(**kwargs)
        self._dots = []
        self._base_pos = []
        with self.canvas:
            Color(*dot_color)
            for _ in range(3):
                self._dots.append(Ellipse(pos=(0, 0), size=(dp(10), dp(10))))
        self.bind(pos=self._layout, size=self._layout)
        self._layout()
        Clock.schedule_once(lambda dt: self._start(), 0.05)

    def _layout(self, *args):
        spacing = dp(20)
        start_x = self.center_x - spacing
        self._base_pos = []
        for i, dot in enumerate(self._dots):
            pos = (start_x + i * spacing - dp(5), self.center_y - dp(5))
            dot.pos = pos
            self._base_pos.append(pos)

    def _start(self):
        for i, dot in enumerate(self._dots):
            Clock.schedule_once(lambda dt, d=dot, idx=i: self._loop(d, idx), i * 0.15)

    def _loop(self, dot, idx):
        base = self._base_pos[idx]
        up = Animation(pos=(base[0], base[1] + dp(9)), d=0.28, t='out_quad')
        down = Animation(pos=base, d=0.28, t='in_quad')
        seq = up + down
        seq.repeat = True
        seq.start(dot)


class NavButton(BoxLayout):
    """A single bottom-nav tab: vector icon + label, highlights when active."""
    def __init__(self, icon_cls, label, on_press=None, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.on_press_cb = on_press
        icon_slot = AnchorLayout(size_hint_y=None, height=dp(26))
        self.icon = icon_cls(color=TEXT_MUTED, icon_size=22)
        icon_slot.add_widget(self.icon)
        self.text_lbl = Label(text=label, font_size='10sp', color=TEXT_MUTED,
                               size_hint_y=None, height=dp(14), bold=True)
        self.add_widget(Widget())
        self.add_widget(icon_slot)
        self.add_widget(self.text_lbl)
        self.add_widget(Widget())
        self.bind(on_touch_down=self._on_touch)

    def _on_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            if isinstance(self.icon, SettingsIcon):
                self.icon.spin(150)
            else:
                self.icon.bounce()
            if self.on_press_cb:
                self.on_press_cb()
            return True
        return False

    def set_active(self, is_active):
        color = ACCENT if is_active else TEXT_MUTED
        self.icon.set_color(color)
        self.text_lbl.color = color


class NavBar(BoxLayout):
    def __init__(self, on_select, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=dp(64), **kwargs)
        with self.canvas.before:
            Color(*SURFACE)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
            Color(*BORDER)
            self._line = Line(points=[], width=1)
        self.bind(pos=self._update, size=self._update)

        self.buttons = {}
        tabs = [
            ('home', HomeIcon, 'HOME'),
            ('settings', SettingsIcon, 'SETTINGS'),
            ('files', FolderIcon, 'FILES'),
            ('about', ProfileIcon, 'ABOUT'),
            ('help', HelpIcon, 'HELP'),
        ]
        for key, icon_cls, label in tabs:
            btn = NavButton(icon_cls, label, on_press=lambda k=key: on_select(k))
            self.buttons[key] = btn
            self.add_widget(btn)
        self.set_active('home')

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.points = [self.x, self.top, self.x + self.width, self.top]

    def set_active(self, key):
        for k, btn in self.buttons.items():
            btn.set_active(k == key)


# ---------- Task row ----------

class TaskRow(Card):
    def __init__(self, url_preview, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(72),
                          padding=[dp(14), dp(10)], spacing=dp(6), radius=18, **kwargs)

        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20))
        self.title_label = Label(
            text=url_preview, font_size='13sp', bold=True, color=TEXT_PRIMARY,
            halign='left', valign='middle', shorten=True, shorten_from='right'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        top.add_widget(self.title_label)

        self.badge = Pill(text="QUEUED", bg=SURFACE_2, fg=TEXT_MUTED)
        top.add_widget(self.badge)
        self.add_widget(top)

        bar_wrap = BoxLayout(size_hint_y=None, height=dp(8))
        self.bar = RoundedProgressBar(max=100, value=0, size_hint_y=None, height=dp(8))
        bar_wrap.add_widget(self.bar)
        self.add_widget(bar_wrap)

        pct_row = BoxLayout(size_hint_y=None, height=dp(16))
        self.pct_label = Label(text="", font_size='10sp', color=TEXT_MUTED, halign='right', valign='middle')
        self.pct_label.bind(size=self.pct_label.setter('text_size'))
        pct_row.add_widget(self.pct_label)
        self.add_widget(pct_row)

    def set_progress(self, pct):
        self.bar.set_value(max(0, min(100, pct)))
        self.pct_label.text = f"{int(pct)}%"


# ---------- Main App ----------

class HenxDownloaderApp(App):

    # ---------- lifecycle ----------

    def build(self):
        self.title = "Henx Downloader"
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.download_dir = "/sdcard/Download"
        self.task_rows = {}
        self.total_count = 0
        self.done_count = 0
        self.fail_count = 0

        # settings state
        self.max_workers = 5
        self.auto_clear = False
        self.notify_on_finish = True
        self.vibrate_on_finish = True
        self.confirm_large_batch = False
        self.keep_screen_on = True
        Window.keep_screen_on = True
        self.theme = 'dark'
        self.is_online = True

        self.root_layout = FloatLayout()

        self.body = BoxLayout(orientation='vertical')
        self.sm = ScreenManager(transition=SlideTransition(duration=0.18))
        self.sm.add_widget(self._build_splash_screen())
        self.sm.add_widget(self._build_home_screen())
        self.sm.add_widget(self._build_settings_screen())
        self.sm.add_widget(self._build_about_screen())
        self.sm.add_widget(self._build_help_screen())
        self.sm.add_widget(self._build_files_screen())
        self.sm.current = 'splash'
        self.body.add_widget(self.sm)

        self.nav_bar = NavBar(on_select=self._switch_screen)
        self.nav_bar.opacity = 0
        self.nav_bar.height = 0
        self.body.add_widget(self.nav_bar)

        self.root_layout.add_widget(self.body)

        Clock.schedule_once(lambda dt: self._leave_splash(), 1.8)
        self._check_connectivity()
        Clock.schedule_interval(lambda dt: self._check_connectivity(), 6)
        Clock.schedule_interval(self._check_connectivity, 5)
        self._check_connectivity(0)

        # toast overlay, sits above everything
        self.toast_label = Label(
            text="", font_size='13sp', bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(260), dp(40)),
            pos_hint={'center_x': 0.5, 'y': 0.12}, opacity=0
        )
        with self.toast_label.canvas.before:
            self._toast_bg_color = Color(0.1, 0.11, 0.14, 0)
            self._toast_bg = RoundedRectangle(pos=self.toast_label.pos, size=self.toast_label.size, radius=[20])
        self.toast_label.bind(pos=self._update_toast_bg, size=self._update_toast_bg)
        self.root_layout.add_widget(self.toast_label)

        return self.root_layout

    def _update_toast_bg(self, *args):
        self._toast_bg.pos = self.toast_label.pos
        self._toast_bg.size = self.toast_label.size

    def show_toast(self, message):
        self.toast_label.text = message
        anim = Animation(opacity=1, d=0.15) + Animation(opacity=1, d=1.4) + Animation(opacity=0, d=0.3)
        bg_anim = Animation(a=0.92, d=0.15) + Animation(a=0.92, d=1.4) + Animation(a=0, d=0.3)
        anim.cancel(self.toast_label)
        anim.start(self.toast_label)
        bg_anim.start(self._toast_bg_color)

    def _switch_screen(self, key):
        order = ['home', 'settings', 'files', 'about', 'help']
        current_idx = order.index(self.sm.current) if self.sm.current in order else 0
        target_idx = order.index(key)
        self.sm.transition.direction = 'left' if target_idx > current_idx else 'right'
        self.sm.current = key
        self.nav_bar.set_active(key)

    def _on_theme_change(self, is_light):
        """Rebuilds the three main screens with the new palette. Any
        text typed into the URL box or an in-progress download list
        resets when you flip this — downloads already running keep
        going in the background either way, since those live on the
        executor, not on the screen widgets."""
        self.theme = 'light' if is_light else 'dark'
        apply_palette(self.theme)

        current = self.sm.current if self.sm.current != 'splash' else 'home'
        self.sm.clear_widgets()
        self.sm.add_widget(self._build_home_screen())
        self.sm.add_widget(self._build_settings_screen())
        self.sm.add_widget(self._build_about_screen())
        self.sm.add_widget(self._build_help_screen())
        self.sm.add_widget(self._build_files_screen())
        self.sm.current = current

        old_nav = self.nav_bar
        self.nav_bar = NavBar(on_select=self._switch_screen)
        self.nav_bar.set_active(current)
        self.body.remove_widget(old_nav)
        self.body.add_widget(self.nav_bar)

        self.show_toast(f"Switched to {self.theme} mode")

    # ---------- Splash screen ----------

    def _build_splash_screen(self):
        screen = Screen(name='splash')
        root = FloatLayout()
        with root.canvas.before:
            Color(0, 0, 0, 1)
            self._splash_bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
        root.bind(pos=self._update_splash_bg, size=self._update_splash_bg)

        center = BoxLayout(orientation='vertical', spacing=dp(18),
                            size_hint=(None, None), size=(dp(140), dp(120)),
                            pos_hint={'center_x': 0.5, 'center_y': 0.5})
        icon_wrap = AnchorLayout(size_hint_y=None, height=dp(64))
        icon_wrap.add_widget(KivyImage(source='icon.png', size_hint=(None, None), size=(dp(64), dp(64))))
        center.add_widget(icon_wrap)

        dots_wrap = AnchorLayout(size_hint_y=None, height=dp(22))
        dots_wrap.add_widget(LoadingDots())
        center.add_widget(dots_wrap)

        root.add_widget(center)
        screen.add_widget(root)
        return screen

    def _update_splash_bg(self, instance, *args):
        self._splash_bg.pos = instance.pos
        self._splash_bg.size = instance.size

    def _check_connectivity(self):
        """Runs the actual (blocking) network probe on a background
        thread so it never freezes the UI, then applies the result back
        on the main thread via Clock.schedule_once — the standard safe
        pattern for touching widgets from outside Kivy's own thread."""
        def worker():
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=2.5)
                online = True
            except OSError:
                online = False
            Clock.schedule_once(lambda dt: self._set_online_status(online))
        threading.Thread(target=worker, daemon=True).start()

    def _set_online_status(self, online):
        changed = online != self.is_online
        self.is_online = online
        if not hasattr(self, 'status_label'):
            return
        color = GOOD if online else BAD
        self.status_label.text = "Online" if online else "Offline"
        self.status_label.color = color
        self.status_dot_color.rgba = color
        if changed:
            self.show_toast("Back online" if online else "You're offline")

    def _leave_splash(self):
        self.sm.current = 'home'
        self.nav_bar.set_active('home')
        self.nav_bar.height = dp(64)
        Animation(opacity=1, d=0.35, t='out_quad').start(self.nav_bar)
        self.send_notification(
            "Henx Downloader",
            "Available whenever you need a download — grab video or audio for free."
        )

    # ---------- Home screen ----------

    def _build_home_screen(self):
        screen = Screen(name='home')
        root = BoxLayout(orientation='vertical', padding=[dp(18), dp(20), dp(18), dp(10)], spacing=dp(14))

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(52), spacing=dp(2))
        title_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        icon_slot = AnchorLayout(size_hint=(None, 1), width=dp(26))
        icon_slot.add_widget(HeaderLogo())
        title_row.add_widget(icon_slot)
        title = Label(
            text="[b]Henx[/b] [color=2ea6ff]Downloader[/color]",
            markup=True, font_size='24sp', halign='left', valign='middle', color=TEXT_PRIMARY
        )
        title.bind(size=title.setter('text_size'))
        title_row.add_widget(title)
        header.add_widget(title_row)

        subtitle_row = BoxLayout(size_hint_y=None, height=dp(18))
        subtitle = Label(
            text="Fast, parallel media downloads", font_size='12sp',
            color=TEXT_MUTED, halign='left', valign='middle'
        )
        subtitle.bind(size=subtitle.setter('text_size'))
        subtitle_row.add_widget(subtitle)

        self.status_dot_color = Color(GOOD if self.is_online else BAD)
        status_wrap = BoxLayout(size_hint=(None, None), size=(dp(90), dp(18)), spacing=dp(5))
        dot_holder = Widget(size_hint=(None, None), size=(dp(8), dp(8)))
        with dot_holder.canvas:
            self.status_dot_color = Color(*(GOOD if self.is_online else BAD))
            self.status_dot = Ellipse(pos=dot_holder.pos, size=dot_holder.size)
        dot_holder.bind(pos=lambda inst, v: setattr(self.status_dot, 'pos', v))
        dot_center = AnchorLayout(size_hint=(None, 1), width=dp(8))
        dot_center.add_widget(dot_holder)
        status_wrap.add_widget(dot_center)
        self.status_label = Label(
            text="Online" if self.is_online else "Offline", font_size='11sp', bold=True,
            color=(GOOD if self.is_online else BAD), halign='left', valign='middle',
            size_hint_x=None, width=dp(70)
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        status_wrap.add_widget(self.status_label)
        subtitle_row.add_widget(status_wrap)

        header.add_widget(subtitle_row)
        root.add_widget(header)

        input_card = Card(orientation='vertical', size_hint_y=None, height=dp(190),
                           padding=dp(16), spacing=dp(10), radius=24)
        input_header = BoxLayout(size_hint_y=None, height=dp(20))
        input_header.add_widget(SectionLabel("SOURCE LINKS"))
        paste_btn = GhostButton(text="Paste", size_hint=(None, None), size=(dp(70), dp(28)), font_size='12sp')
        paste_btn.bind(on_press=self.paste_clipboard)
        paste_wrap = BoxLayout(size_hint_y=None, height=dp(28))
        paste_wrap.add_widget(Widget())
        paste_wrap.add_widget(paste_btn)
        input_header.add_widget(paste_wrap)
        input_card.add_widget(input_header)

        self.url_input = RoundedTextInput(
            hint_text="Paste one or more links, one per line...",
            multiline=True,
        )
        input_card.add_widget(self.url_input)
        root.add_widget(input_card)

        options_card = Card(orientation='vertical', size_hint_y=None, height=dp(96),
                             padding=dp(16), spacing=dp(10), radius=24)
        options_card.add_widget(SectionLabel("OPTIONS"))

        opt_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(12))

        quality_wrap = BoxLayout(orientation='vertical', spacing=dp(2))
        quality_wrap.add_widget(Label(text="Quality", font_size='10sp', color=TEXT_MUTED,
                                       size_hint_y=None, height=dp(14), halign='left'))
        self.quality_spinner = RoundedSpinner(
            text='Best', values=('Best', '1080p', '720p', '480p', '360p'),
            size_hint_y=None, height=dp(36),
            font_size='13sp'
        )
        quality_wrap.add_widget(self.quality_spinner)
        opt_row.add_widget(quality_wrap)

        audio_wrap = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_x=0.55)
        audio_wrap.add_widget(Label(text="Audio only (MP3)", font_size='10sp', color=TEXT_MUTED,
                                     size_hint_y=None, height=dp(14), halign='left'))
        audio_row = BoxLayout(size_hint_y=None, height=dp(36))
        self.audio_toggle = ToggleSwitch()
        audio_center = BoxLayout()
        audio_center.add_widget(self.audio_toggle)
        audio_row.add_widget(audio_center)
        audio_wrap.add_widget(audio_row)
        opt_row.add_widget(audio_wrap)

        options_card.add_widget(opt_row)
        root.add_widget(options_card)

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(52))
        self.start_btn = GradientButton(text="  START DOWNLOAD", c1=ACCENT, font_size='14sp', show_play_icon=True)
        self.start_btn.bind(on_press=self.start_downloads)
        btn_row.add_widget(self.start_btn)

        clear_btn = GhostButton(text="Clear Links", size_hint_x=0.4, font_size='12sp')
        clear_btn.bind(on_press=self.clear_input)
        btn_row.add_widget(clear_btn)
        root.add_widget(btn_row)

        tasks_header = BoxLayout(size_hint_y=None, height=dp(22))
        tasks_title = Label(
            text="ACTIVE TASKS", font_size='12sp', bold=True, color=TEXT_MUTED,
            halign='left', valign='middle'
        )
        tasks_title.bind(size=tasks_title.setter('text_size'))
        tasks_header.add_widget(tasks_title)

        self.summary_badge = SummaryBadge()
        tasks_header.add_widget(self.summary_badge)
        root.add_widget(tasks_header)

        clear_done_btn = GhostButton(text="Clear Completed", size_hint_y=None, height=dp(32), font_size='11sp')
        clear_done_btn.bind(on_press=self.clear_completed)
        root.add_widget(clear_done_btn)

        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_type=['bars', 'content'],
            bar_width=dp(5),
            bar_color=ACCENT,
            bar_inactive_color=(*BORDER[:3], 0.6),
            bar_margin=dp(2),
            scroll_distance=dp(8),
            scroll_timeout=250,
            always_overscroll=True,
        )
        self.status_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, padding=[0, dp(4)])
        self.status_box.bind(minimum_height=self.status_box.setter('height'))
        scroll.add_widget(self.status_box)
        root.add_widget(scroll)

        screen.add_widget(root)
        return screen

    # ---------- Settings screen ----------

    def _build_settings_screen(self):
        screen = Screen(name='settings')
        root = BoxLayout(orientation='vertical', padding=[dp(18), dp(20), dp(18), dp(10)], spacing=dp(14))

        title = Label(text="Settings", font_size='22sp', bold=True, color=TEXT_PRIMARY,
                      halign='left', valign='middle', size_hint_y=None, height=dp(34))
        title.bind(size=title.setter('text_size'))
        root.add_widget(title)

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(14), size_hint_y=None, padding=[0, dp(4)])
        content.bind(minimum_height=content.setter('height'))

        # appearance card
        appearance_card = Card(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(4), radius=24)
        appearance_card.add_widget(SectionLabel("APPEARANCE"))
        theme_toggle = ToggleSwitch(active=(self.theme == 'light'), on_change=self._on_theme_change)
        appearance_card.add_widget(SettingsRow("Light Mode", theme_toggle))

        confirm_toggle = ToggleSwitch(active=self.confirm_large_batch, on_change=self._on_confirm_batch_change)
        appearance_card.add_widget(SettingsRow(
            "Confirm large batches", confirm_toggle,
            subtitle="Ask before starting 6+ downloads at once"
        ))

        screen_on_toggle = ToggleSwitch(active=self.keep_screen_on, on_change=self._on_screen_on_change)
        appearance_card.add_widget(SettingsRow(
            "Keep screen on", screen_on_toggle,
            subtitle="Stop the screen sleeping while downloads run"
        ))
        appearance_card.height = dp(40) + dp(56) * 3 + dp(10)
        content.add_widget(appearance_card)

        # downloads card
        dl_card = Card(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(4), radius=24)
        dl_card.add_widget(SectionLabel("DOWNLOADS"))

        self.workers_value_label = Label(text="5", font_size='14sp', bold=True, color=ACCENT,
                                          size_hint=(None, None), size=(dp(30), dp(30)))
        workers_slider = Slider(min=1, max=10, value=5, step=1, size_hint_x=1)
        workers_slider.bind(value=self._on_workers_change)
        workers_row = SettingsRow(
            "Parallel downloads", workers_slider,
            subtitle="How many links download at once"
        )
        dl_card.add_widget(workers_row)
        dl_card.add_widget(self.workers_value_label)

        auto_clear_toggle = ToggleSwitch(active=False, on_change=self._on_auto_clear_change)
        dl_card.add_widget(SettingsRow(
            "Auto-clear completed", auto_clear_toggle,
            subtitle="Remove finished tasks once all are done"
        ))

        notify_toggle = ToggleSwitch(active=True, on_change=self._on_notify_change)
        dl_card.add_widget(SettingsRow(
            "Toast on finish", notify_toggle,
            subtitle="Show a message when downloads complete"
        ))

        vibrate_toggle = ToggleSwitch(active=True, on_change=self._on_vibrate_change)
        dl_card.add_widget(SettingsRow(
            "Vibrate on finish", vibrate_toggle,
            subtitle="Quick buzz when a download finishes or fails"
        ))
        dl_card.height = dp(40) + dp(56) * 4 + dp(10)
        content.add_widget(dl_card)

        # storage card
        storage_card = Card(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(8), radius=24)
        storage_card.add_widget(SectionLabel("STORAGE"))
        self.storage_path_label = Label(
            text=self.download_dir, font_size='12sp', color=TEXT_MUTED,
            halign='left', valign='middle', size_hint_y=None, height=dp(20)
        )
        self.storage_path_label.bind(size=self.storage_path_label.setter('text_size'))
        storage_card.add_widget(self.storage_path_label)

        subfolder_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        self.subfolder_input = RoundedTextInput(
            hint_text="Optional subfolder name...", multiline=False,
            size_hint_y=None, height=dp(40), font_size='12sp'
        )
        apply_btn = GhostButton(text="Set", size_hint_x=None, width=dp(60), font_size='12sp')
        apply_btn.bind(on_press=self._apply_subfolder)
        subfolder_row.add_widget(self.subfolder_input)
        subfolder_row.add_widget(apply_btn)
        storage_card.add_widget(subfolder_row)

        storage_card.height = dp(126)
        content.add_widget(storage_card)

        # reset card
        reset_card = Card(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(10), radius=24)
        reset_card.add_widget(SectionLabel("RESET"))
        reset_btn = GhostButton(text="Restore Default Settings", size_hint_y=None, height=dp(42), font_size='13sp')
        reset_btn.bind(on_press=self._reset_settings)
        reset_card.add_widget(reset_btn)
        reset_card.height = dp(96)
        content.add_widget(reset_card)

        scroll.add_widget(content)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def _on_workers_change(self, instance, value):
        self.max_workers = int(value)
        self.workers_value_label.text = str(int(value))

    def _on_auto_clear_change(self, active):
        self.auto_clear = active

    def _on_notify_change(self, active):
        self.notify_on_finish = active

    def _on_vibrate_change(self, active):
        self.vibrate_on_finish = active

    def _on_confirm_batch_change(self, active):
        self.confirm_large_batch = active

    def _on_screen_on_change(self, active):
        self.keep_screen_on = active
        Window.keep_screen_on = active

    def _apply_subfolder(self, instance):
        name = self.subfolder_input.text.strip()
        # strip anything that could break out of the intended folder
        name = name.replace("..", "").replace("/", "").replace("\\", "")
        base = "/sdcard/Download"
        self.download_dir = os.path.join(base, name) if name else base
        try:
            os.makedirs(self.download_dir, exist_ok=True)
        except Exception:
            pass
        self.storage_path_label.text = self.download_dir
        self.show_toast("Downloads will save to: " + self.download_dir)

    def _reset_settings(self, instance):
        self.max_workers = 5
        self.auto_clear = False
        self.notify_on_finish = True
        self.vibrate_on_finish = True
        self.download_dir = "/sdcard/Download"
        self.show_toast("Settings restored to default")

    # ---------- About screen ----------

    def _build_about_screen(self):
        screen = Screen(name='about')
        root = BoxLayout(orientation='vertical', padding=[dp(18), dp(20), dp(18), dp(10)], spacing=dp(16))

        title = Label(text="About", font_size='22sp', bold=True, color=TEXT_PRIMARY,
                      halign='left', valign='middle', size_hint_y=None, height=dp(34))
        title.bind(size=title.setter('text_size'))
        root.add_widget(title)

        badge_wrap = BoxLayout(size_hint_y=None, height=dp(56))
        badge_wrap.add_widget(Widget())
        badge = KivyImage(source='icon.png', size_hint=(None, None), size=(dp(56), dp(56)))
        badge_wrap.add_widget(badge)
        badge_wrap.add_widget(Widget())
        root.add_widget(badge_wrap)

        name_label = Label(text="[b]Henx Downloader[/b]", markup=True, font_size='19sp',
                            color=TEXT_PRIMARY, size_hint_y=None, height=dp(28))
        root.add_widget(name_label)

        version_label = Label(text="Version 1.0", font_size='12sp', color=TEXT_MUTED,
                               size_hint_y=None, height=dp(18))
        root.add_widget(version_label)

        tagline = Label(text="Fast, parallel media downloads\nfor video and audio links.",
                         font_size='12sp', color=TEXT_MUTED, halign='center',
                         size_hint_y=None, height=dp(40))
        root.add_widget(tagline)

        credits_card = Card(orientation='vertical', size_hint_y=None, height=dp(110),
                             padding=dp(16), spacing=dp(6), radius=24)
        credits_card.add_widget(SectionLabel("BUILT WITH"))
        for line in ["Kivy — UI framework", "yt-dlp — download engine"]:
            lbl = Label(text=line, font_size='12sp', color=TEXT_PRIMARY, halign='left', valign='middle',
                        size_hint_y=None, height=dp(20))
            lbl.bind(size=lbl.setter('text_size'))
            credits_card.add_widget(lbl)
        root.add_widget(credits_card)

        dev_card = Card(orientation='vertical', size_hint_y=None, height=dp(64),
                         padding=dp(16), spacing=dp(4), radius=24)
        dev_card.add_widget(SectionLabel("DEVELOPER"))
        dev_label = Label(text="Made by Henx", font_size='13sp', color=TEXT_PRIMARY,
                           halign='left', valign='middle', size_hint_y=None, height=dp(20))
        dev_label.bind(size=dev_label.setter('text_size'))
        dev_card.add_widget(dev_label)
        root.add_widget(dev_card)

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(46))
        share_btn = GhostButton(text="Share App", font_size='13sp')
        share_btn.bind(on_press=self.share_app)
        rate_btn = GhostButton(text="Rate App", font_size='13sp')
        rate_btn.bind(on_press=lambda x: self.show_toast("Thanks for the support!"))
        btn_row.add_widget(share_btn)
        btn_row.add_widget(rate_btn)
        root.add_widget(btn_row)

        support_btn = GhostButton(text="Support the Creator", size_hint_y=None, height=dp(46), font_size='13sp')
        support_btn.bind(on_press=self.support_creator)
        root.add_widget(support_btn)

        root.add_widget(Widget())
        screen.add_widget(root)
        return screen

    # ---------- Help screen ----------

    def _build_help_screen(self):
        screen = Screen(name='help')
        root = BoxLayout(orientation='vertical', padding=[dp(18), dp(20), dp(18), dp(10)], spacing=dp(14))

        title = Label(text="How to Download", font_size='22sp', bold=True, color=TEXT_PRIMARY,
                      halign='left', valign='middle', size_hint_y=None, height=dp(34))
        title.bind(size=title.setter('text_size'))
        root.add_widget(title)

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(14), size_hint_y=None, padding=[0, dp(4)])
        content.bind(minimum_height=content.setter('height'))

        steps = [
            ("1. Paste your link(s)", "Copy a video or audio link, then tap Paste on the Home screen. You can paste more than one — just put each link on its own line."),
            ("2. Pick your options", "Choose a quality (Best is the max available), or flip on Audio Only if you just want the MP3."),
            ("3. Tap Start Download", "Every link you pasted downloads at the same time, up to the parallel-download limit you set in Settings."),
            ("4. Check Active Tasks", "Each link gets its own progress bar and status badge — Queued, Downloading, Done, or Failed."),
            ("Where do files go?", "Everything saves to your phone's normal Download folder, same place your browser saves files."),
        ]

        for heading, body in steps:
            card = Card(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(6), radius=24)
            head_lbl = Label(text=heading, font_size='14sp', bold=True, color=ACCENT,
                              halign='left', valign='middle', size_hint_y=None, height=dp(22))
            head_lbl.bind(size=head_lbl.setter('text_size'))
            card.add_widget(head_lbl)
            body_lbl = Label(text=body, font_size='12sp', color=TEXT_MUTED,
                              halign='left', valign='top', size_hint_y=None)
            body_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
            body_lbl.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))
            card.add_widget(body_lbl)
            card.bind(minimum_height=card.setter('height'))
            content.add_widget(card)

        scroll.add_widget(content)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    # ---------- Files screen ----------

    def _build_files_screen(self):
        screen = Screen(name='files')
        root = BoxLayout(orientation='vertical', padding=[dp(18), dp(20), dp(18), dp(10)], spacing=dp(14))

        header_row = BoxLayout(size_hint_y=None, height=dp(34))
        title = Label(text="Downloads", font_size='22sp', bold=True, color=TEXT_PRIMARY,
                      halign='left', valign='middle')
        title.bind(size=title.setter('text_size'))
        header_row.add_widget(title)
        refresh_btn = GhostButton(text="Refresh", size_hint=(None, None), size=(dp(80), dp(32)), font_size='12sp')
        refresh_btn.bind(on_press=lambda x: self._refresh_files_list())
        header_row.add_widget(refresh_btn)
        root.add_widget(header_row)

        self.files_scroll = ScrollView(size_hint=(1, 1))
        self.files_content = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, padding=[0, dp(4)])
        self.files_content.bind(minimum_height=self.files_content.setter('height'))
        self.files_scroll.add_widget(self.files_content)
        root.add_widget(self.files_scroll)

        screen.bind(on_pre_enter=lambda inst: self._refresh_files_list())
        screen.add_widget(root)
        return screen

    def _refresh_files_list(self):
        self.files_content.clear_widgets()
        try:
            entries = []
            if os.path.isdir(self.download_dir):
                for name in os.listdir(self.download_dir):
                    full = os.path.join(self.download_dir, name)
                    if os.path.isfile(full):
                        entries.append((name, os.path.getsize(full), os.path.getmtime(full)))
            entries.sort(key=lambda e: e[2], reverse=True)
        except Exception:
            entries = []

        if not entries:
            empty = Label(
                text="No downloads yet — finished files will show up here.",
                font_size='13sp', color=TEXT_MUTED, halign='center',
                size_hint_y=None, height=dp(60)
            )
            self.files_content.add_widget(empty)
            return

        for name, size_bytes, _ in entries:
            card = Card(orientation='horizontal', size_hint_y=None, height=dp(56),
                        padding=dp(12), spacing=dp(10), radius=18)
            name_label = Label(
                text=name, font_size='12sp', color=TEXT_PRIMARY,
                halign='left', valign='middle', shorten=True, shorten_from='right'
            )
            name_label.bind(size=name_label.setter('text_size'))
            card.add_widget(name_label)
            size_label = Label(
                text=self._format_size(size_bytes), font_size='11sp', color=TEXT_MUTED,
                halign='right', valign='middle', size_hint_x=None, width=dp(70)
            )
            size_label.bind(size=size_label.setter('text_size'))
            card.add_widget(size_label)
            self.files_content.add_widget(card)

    @staticmethod
    def _format_size(num_bytes):
        size = float(num_bytes)
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f"{size:.0f} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ---------- UI actions ----------

    def clear_input(self, instance):
        self.url_input.text = ""

    def paste_clipboard(self, instance):
        clip = Clipboard.paste()
        if clip:
            current = self.url_input.text
            sep = "\n" if current and not current.endswith("\n") else ""
            self.url_input.text = current + sep + clip.strip() + "\n"

    def clear_completed(self, instance=None):
        for key, row in list(self.task_rows.items()):
            if row.badge.label.text in ("DONE", "FAILED"):
                self.status_box.remove_widget(row)
                del self.task_rows[key]

    def update_summary(self):
        self.summary_badge.update(self.done_count, self.fail_count, self.total_count)
        if self.auto_clear and self.total_count > 0 and (self.done_count + self.fail_count) == self.total_count:
            Clock.schedule_once(lambda dt: self.clear_completed(), 0.6)

    def share_app(self, instance=None):
        """Shares a text message about the app via Android's native share
        sheet. This used to try sharing the raw installed APK file
        directly, but that reliably fails on Android 7+ without a
        FileProvider — a piece of native Android manifest configuration
        that needs custom XML resources, not something safely added
        blind through buildozer.spec after tonight's build history.
        Sharing text needs no such setup and actually works."""
        from kivy.utils import platform
        if platform != 'android':
            self.show_toast("Sharing only works on the installed Android app")
            return
        try:
            from plyer import share
            share.share_text(
                "Check out Henx Downloader — grab video or audio for free. "
                "Ask me for the APK and I'll send it over!",
                title="Henx Downloader"
            )
        except Exception:
            self.show_toast("Couldn't open the share sheet on this device")

    def support_creator(self, instance=None):
        """Opens the phone's email app with a message addressed to the
        creator, via plyer's email facade (same trusted library already
        used for sharing/notifications/vibration)."""
        try:
            from plyer import email
            email.send(
                recipient="henxkcee03@gmail.com",
                subject="Henx Downloader — Support",
                create_chooser=True
            )
        except Exception:
            self.show_toast("Couldn't open an email app on this device")

    def send_notification(self, title, message):
        """Fires a real Android system notification (visible even if the
        app isn't in the foreground). Falls back silently to nothing on
        non-Android platforms or if the OS blocks it — this never raises,
        so it can't take the app down if a device denies permission."""
        from kivy.utils import platform
        if platform != 'android':
            return
        try:
            from plyer import notification
            notification.notify(title=title, message=message, app_name="Henx Downloader")
        except Exception:
            pass

    # ---------- download logic ----------

    def start_downloads(self, instance):
        urls = [u.strip() for u in self.url_input.text.splitlines() if u.strip()]
        if not urls:
            self.status_box.clear_widgets()
            row = TaskRow("Please paste at least one URL.")
            row.badge.set("WARN", (0.35, 0.28, 0.1, 1), WARN)
            self.status_box.add_widget(row)
            return

        if not self.is_online:
            self.show_toast("No internet connection right now")
            return

        if self.confirm_large_batch and len(urls) >= 6:
            self._confirm_batch_popup(urls)
            return

        self._run_downloads(urls)

    def _confirm_batch_popup(self, urls):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(14))
        msg = Label(
            text=f"Start {len(urls)} downloads at once?",
            font_size='14sp', color=TEXT_PRIMARY
        )
        content.add_widget(msg)
        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(44))
        cancel_btn = GhostButton(text="Cancel", font_size='13sp')
        confirm_btn = GradientButton(text="Start", c1=ACCENT, font_size='13sp')
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(confirm_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title="Confirm batch download", content=content,
            size_hint=(0.85, None), height=dp(160),
            separator_color=ACCENT, title_color=TEXT_PRIMARY,
            background_color=SURFACE
        )
        cancel_btn.bind(on_press=popup.dismiss)

        def _confirmed(instance):
            popup.dismiss()
            self._run_downloads(urls)
        confirm_btn.bind(on_press=_confirmed)
        popup.open()

    def _run_downloads(self, urls):
        # rebuild the executor if the user changed the parallel-download
        # count in Settings since the last run
        if self.executor._max_workers != self.max_workers:
            self.executor.shutdown(wait=False)
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        self.status_box.clear_widgets()
        self.task_rows = {}
        self.total_count = len(urls)
        self.done_count = 0
        self.fail_count = 0
        self.update_summary()
        self.show_toast(f"Started {len(urls)} download(s)")

        for i, url in enumerate(urls):
            row = TaskRow(url[:40] + ("..." if len(url) > 40 else ""))
            self.status_box.add_widget(row)
            self.task_rows[i] = row
            self.executor.submit(self.download_worker, i, url)

    def build_ydl_opts(self, task_id):
        audio_only = self.audio_toggle.active
        quality = self.quality_spinner.text

        if audio_only:
            fmt = 'bestaudio/best'
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            postprocessors = []
            if quality == 'Best':
                fmt = 'best'
            else:
                height = quality.replace('p', '')
                fmt = f'best[height<={height}]/best'

        return {
            'format': fmt,
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'postprocessors': postprocessors,
            'progress_hooks': [lambda d, tid=task_id: self.progress_hook(tid, d)],
        }

    def progress_hook(self, task_id, d):
        if d.get('status') == 'downloading':
            pct_str = d.get('_percent_str', '0%').strip().replace('%', '')
            try:
                pct = float(pct_str)
            except ValueError:
                pct = 0
            Clock.schedule_once(lambda dt: self._update_progress(task_id, pct))
        elif d.get('status') == 'finished':
            Clock.schedule_once(lambda dt: self._update_progress(task_id, 100))

    def _update_progress(self, task_id, pct):
        row = self.task_rows.get(task_id)
        if row:
            row.set_progress(pct)
            row.badge.set("DOWNLOADING", (0.16, 0.24, 0.34, 1), ACCENT)

    def download_worker(self, task_id, url):
        ydl_opts = self.build_ydl_opts(task_id)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title')[:38]
                Clock.schedule_once(lambda dt: self._set_row(task_id, title))
                ydl.download([url])
                Clock.schedule_once(lambda dt: self._finish_row(task_id, title, success=True))
        except Exception:
            Clock.schedule_once(lambda dt: self._finish_row(task_id, "Link failed", success=False))

    def _set_row(self, task_id, title):
        row = self.task_rows.get(task_id)
        if row:
            row.title_label.text = title
            row.badge.set("DOWNLOADING", (0.16, 0.24, 0.34, 1), ACCENT)

    def _finish_row(self, task_id, title, success):
        row = self.task_rows.get(task_id)
        if row:
            row.title_label.text = title
            if success:
                row.badge.set("DONE", (0.13, 0.28, 0.19, 1), GOOD)
                row.set_progress(100)
            else:
                row.badge.set("FAILED", (0.32, 0.14, 0.15, 1), BAD)
        if success:
            self.done_count += 1
        else:
            self.fail_count += 1
        if self.notify_on_finish:
            self.show_toast(f"{'Done' if success else 'Failed'}: {title}")
            self.send_notification(
                "Download complete" if success else "Download failed",
                title
            )
        if self.vibrate_on_finish:
            self.vibrate_device()
        self.update_summary()

    def vibrate_device(self, duration=0.15):
        """Short buzz on download finish/fail. Guarded the same way as
        notifications and sharing — silently does nothing if unsupported
        rather than risking a crash."""
        from kivy.utils import platform
        if platform != 'android':
            return
        try:
            from plyer import vibrator
            vibrator.vibrate(duration)
        except Exception:
            pass


if __name__ == "__main__":
    HenxDownloaderApp().run()
