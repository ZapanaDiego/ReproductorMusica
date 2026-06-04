# ==========================================
# ARCHIVO: ui/visualizer.py
# ==========================================
import random
from textual.widgets import Static
from rich.text import Text

CAVA_CHARS = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
DECAY = 0.85
SPARK_THRESHOLD = 0.35
AUTO_GAIN_CEILING = 0.2


class CavaVisualizer(Static):
    """
    Ecualizador CAVA a pantalla completa: autoganancia, gravedad suave
    y partículas con drift horizontal.
    """
    DEFAULT_CSS = """
    CavaVisualizer {
        width: 1fr;
        height: 1fr;
        color: auto;
        background: transparent;
    }
    """

    def on_mount(self):
        self.particles = []
        self.previous_bars = []
        self.set_interval(0.033, self.update_visualizer)

    def update_visualizer(self):
        bridge = self.app.bridge
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return

        bars = list(bridge.get_cava_data(w))

        peak = max(bars) if bars else 0.0
        if 0.0 < peak < AUTO_GAIN_CEILING:
            gain = 1.0 / peak
            bars = [min(1.0, b * gain) for b in bars]

        if len(self.previous_bars) != w:
            self.previous_bars = [0.0] * w

        smoothed = []
        for i, raw in enumerate(bars):
            prev = self.previous_bars[i]
            if raw > prev:
                smoothed.append(raw)
            else:
                smoothed.append(prev * DECAY)
        self.previous_bars = smoothed
        bars = smoothed

        active = []
        for p in self.particles:
            p['y'] -= p['speed_y']
            p['x'] += p['speed_x']
            if 0 <= p['y'] < h and 0 <= p['x'] < w:
                active.append(p)
        self.particles = active

        for x, val in enumerate(bars):
            if val > SPARK_THRESHOLD and random.random() < 0.12:
                self.particles.append({
                    'x': float(x),
                    'y': float(h - 1 - int(val * max(1, h - 1))),
                    'char': random.choice(['*', '+', '•', '°']),
                    'color': random.choice(['#FFFF00', '#00FFFF', '#FF00FF']),
                    'speed_y': random.uniform(0.4, 1.0),
                    'speed_x': random.uniform(-0.6, 0.6),
                })

        particle_map = {}
        for p in self.particles:
            px, py = int(p['x']), int(p['y'])
            if 0 <= px < w and 0 <= py < h:
                particle_map[(px, py)] = p

        lines = []
        for y in range(h):
            ratio = y / max(h, 1)
            if ratio < 0.35:
                color = '#FF00FF'
            elif ratio < 0.70:
                color = '#8A2BE2'
            else:
                color = '#00FFFF'

            line_text = Text()
            for x in range(w):
                val = bars[x]
                bar_top = h - 1 - int(val * h)
                char_to_draw = ' '

                if y >= bar_top:
                    dist_from_floor = h - 1 - y
                    bar_span = max(1, h - bar_top)
                    rel = dist_from_floor / bar_span
                    if rel >= 0.92:
                        char_to_draw = '█'
                    elif rel >= 0.55:
                        idx = int((rel - 0.55) / 0.37 * (len(CAVA_CHARS) - 2)) + 1
                        char_to_draw = CAVA_CHARS[max(1, min(idx, len(CAVA_CHARS) - 1))]
                    else:
                        char_to_draw = CAVA_CHARS[1]

                p = particle_map.get((x, y))
                if p is not None:
                    line_text.append(p['char'], style=f'bold {p["color"]}')
                elif char_to_draw != ' ':
                    line_text.append(char_to_draw, style=f'bold {color}')
                else:
                    line_text.append(' ')

            lines.append(line_text)

        self.update(Text('\n').join(lines))
