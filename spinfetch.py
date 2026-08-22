#!/usr/bin/env python3
"""fastfetch с вращающимся 3D ASCII-логотипом.

Логотип — твёрдое 3D-тело: передняя/задняя грани + боковые стенки
по контуру, освещение по нормалям (Ламберт). Крутится непрерывно:
влево вокруг вертикальной оси + по диагонали. Каждые CYCLE секунд —
полный оборот, логотип точно встаёт в исходное положение (пиксель-в-пиксель).
Справа — обычный вывод fastfetch.

Использование: spinfetch.py [файл_логотипа]
"""
import math
import os
import shutil
import signal
import subprocess
import sys
import time

LOGO_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/archl")
CYCLE = 12.0          # сек: полный оборот, логотип встаёт в исходное положение
FPS = 30
RESET = "\033[0m"
WHITE = (255, 255, 255)
ARCH_BLUE = (23, 147, 209)      # #1793D1
DEPTH = 4.0                     # толщина тела в клетках
PERSPECTIVE = 40.0              # расстояние до наблюдателя (в клетках)
AMBIENT = 0.45                  # фоновая освещённость

# Свет сверху-справа-спереди; почти фронтальный, чтобы в исходном
# положении цвета оставались практически исходными.
_len = math.sqrt(0.25 * 0.25 + (-0.35) * (-0.35) + 0.9 * 0.9)
LIGHT = (0.25 / _len, -0.35 / _len, 0.9 / _len)

WALL_CHARS = ("▒", "▓", "█")    # стенки: плотность по освещённости

FRONT_Z = DEPTH / 2
WALL_ZS = [FRONT_Z - 1 - i for i in range(int(DEPTH) - 1)]  # 2..-2


def base_color(rows, r, c):
    """Белая окантовка (клетка у края силуэта), внутри — синий Arch."""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < len(rows) and 0 <= cc < len(rows[rr])) or rows[rr][cc] == " ":
                return WHITE
    return ARCH_BLUE


def load_logo():
    with open(LOGO_PATH, encoding="utf-8") as f:
        rows = [line.rstrip("\n") for line in f]
    while rows and not rows[-1].strip():
        rows.pop()
    while rows and not rows[0].strip():
        rows.pop(0)
    grid = [row.ljust(max(map(len, rows))) for row in rows]

    points = []  # (x, y, z, ch|None, rgb, нормаль); None -> символ стенки по яркости
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == " ":
                continue
            rgb = base_color(grid, r, c)
            # передняя и задняя грань
            points.append((float(c), float(r), FRONT_Z, ch, rgb, (0.0, 0.0, 1.0)))
            points.append((float(c), float(r), -FRONT_Z, ch, rgb, (0.0, 0.0, -1.0)))
            # боковые стенки: для каждого «пустого» соседа — стенка с нормалью наружу
            added = set()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    inside = 0 <= rr < len(grid) and 0 <= cc < len(grid[rr]) and grid[rr][cc] != " "
                    if not inside:
                        n = (-dc, -dr)
                        key = n[0] * 10 + n[1]
                        if key in added:
                            continue
                        added.add(key)
                        ln = math.hypot(*n)
                        normal = (n[0] / ln, n[1] / ln, 0.0)
                        for z in WALL_ZS:
                            points.append((float(c), float(r), z, None, rgb, normal))
    return points, len(grid[0]), len(grid)


def rotate3(p, ay, ad):
    """Вращение точки/вектора: вокруг Y (влево), затем вокруг диагонали (1,1,0)/√2."""
    x, y, z = p
    if ay:
        c, s = math.cos(ay), math.sin(ay)
        x, z = x * c + z * s, -x * s + z * c
    if ad:
        k = math.sqrt(0.5)
        c, s = math.cos(ad), math.sin(ad)
        dot = k * x + k * y
        x, y, z = (x * c - k * z * s + k * dot * (1 - c),
                   y * c + k * z * s + k * dot * (1 - c),
                   z * c + k * (y - x) * s)
    return x, y, z


def angles(t):
    """Непрерывное вращение с постоянной скоростью, угол растёт без
    ограничений (без mod): логотип проходит исходное положение на полной
    скорости, без паузы и разворота. Каждые CYCLE секунд угол кратен 2π —
    ориентация точно исходная."""
    w = 2 * math.pi * t / CYCLE
    return -w, w   # влево вокруг вертикальной оси + по диагонали


def render(points, ay, ad, width, height):
    """Проекция с перспективой, z-буфер (ближе = больше z),
    освещение по нормалям. Возвращает (col,row) -> (z, символ, цвет)."""
    cx, cy = (width - 1) / 2.0, height / 2.0
    buf = {}
    for px, py, pz, ch, rgb, normal in points:
        x, y, z = rotate3((px - cx, py - cy, pz), ay, ad)
        nx, ny, nz = rotate3(normal, ay, ad)
        bright = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])
        # нормируем так, чтобы фронтальная грань имела яркость ровно 1.0 —
        # в исходном положении цвета точно исходные, без скачка при возврате
        bright = min(1.0, bright / LIGHT[2])
        shade = AMBIENT + (1.0 - AMBIENT) * bright
        if ch is None:
            ch = WALL_CHARS[min(2, int(bright * 3))]
        ix = round(cx + x * ((PERSPECTIVE - FRONT_Z) / (PERSPECTIVE - z)))
        iy = round(cy + y * ((PERSPECTIVE - FRONT_Z) / (PERSPECTIVE - z)))
        if 0 <= iy <= height and -width <= ix <= width * 2:
            key = (ix, iy)
            if key not in buf or z > buf[key][0]:
                buf[key] = (z, ch, tuple(min(255, round(v * shade)) for v in rgb))
    return buf


def get_fastfetch_info():
    try:
        out = subprocess.run(
            ["fastfetch", "--pipe", "--logo", "none"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        return out.rstrip("\n").split("\n")
    except Exception:
        return ["fastfetch недоступен"]


def main():
    points, width, height = load_logo()
    info = get_fastfetch_info()

    sys.stdout.write("\033[?25l")  # спрятать курсор
    start = time.monotonic()

    def restore(*_):
        sys.stdout.write("\033[?25h" + RESET + "\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, restore)
    signal.signal(signal.SIGTERM, restore)

    frame_time = 1.0 / FPS
    try:
        while True:
            t = time.monotonic() - start
            ay, ad = angles(t)
            buf = render(points, ay, ad, width, height)

            out = ["\033[H"]  # курсор в левый верхний угол
            rows = max(height + 2, len(info))
            cols = width + 2
            for row in range(rows):
                line = []
                vis = 0
                cur_rgb = None
                for col in range(cols):
                    cell = buf.get((col - 1, row - 1))
                    if cell:
                        _, ch, rgb = cell
                        if rgb != cur_rgb:
                            line.append(f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m")
                            cur_rgb = rgb
                        line.append(ch)
                        vis += 1
                    else:
                        line.append(" ")
                        cur_rgb = None
                        vis += 1
                info_line = info[row] if row < len(info) else ""
                out.append("".join(line) + " " * (cols - vis) + RESET + "  " + info_line + "\033[K\n")
            sys.stdout.write("".join(out))
            sys.stdout.flush()

            delay = frame_time - (time.monotonic() - start - t) % frame_time
            if delay > 0:
                time.sleep(delay)
    finally:
        sys.stdout.write("\033[?25h" + RESET)


if __name__ == "__main__":
    if not shutil.which("fastfetch"):
        print("fastfetch не найден в PATH", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(LOGO_PATH):
        print(f"Логотип не найден: {LOGO_PATH}", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write("\033[2J")  # очистить экран
    main()
