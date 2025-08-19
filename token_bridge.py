# duck_notebook.py
# Minimal, cute, scribbly notebook with a duck.
# - Paint ONE ROW of "colours as digits".
# - Space cycles blank→0→1→…→9→blank.
# - Number keys 0–9 set the cell directly.
# - ← / → moves the cursor.
# - Backspace blanks the cell.
# - C clears the whole row.
# - Enter SAVES the current row into the Program panel (right).
# - Click a saved row to load it back for tweaking.
# - Q quits.  (No run, no ops, no interpreter.)

import pygame, math, random, time

# ───────── window / layout ─────────
W, H = 1280, 740
FPS = 60

# grid (one editable row)
CELL = 36
ROW_LEN = 24
GRID_X = 40
GRID_Y = 200

# program panel (saved rows)
GAP = 24
SAVED_X = GRID_X + ROW_LEN * CELL + GAP
SAVED_W = 300
SAVED_Y = GRID_Y - 24

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Duck Notebook — one line at a time")
clock = pygame.time.Clock()
try:
    font = pygame.font.SysFont("Comic Sans MS", 22)
    font_s = pygame.font.SysFont("Comic Sans MS", 16)
    font_tiny = pygame.font.SysFont("Comic Sans MS", 12)
except:
    # fallback if Comic Sans is missing
    font = pygame.font.SysFont("consolas", 20)
    font_s = pygame.font.SysFont("consolas", 16)
    font_tiny = pygame.font.SysFont("consolas", 12)

# ───────── palette & colours ─────────
PAPER  = (245, 242, 236)
INK    = (40, 42, 46)
PALE   = (220, 220, 228)
GRID_LINE = (185, 185, 192)
HILITE = (255, 225, 140)

PALETTE = {
    -1: (245, 242, 236),  # blank (paper)
     0: (230, 232, 235),
     1: (74, 144, 226),
     2: (80, 227, 194),
     3: (255, 206, 84),
     4: (255, 140, 120),
     5: (162, 155, 254),
     6: (255, 159, 67),
     7: (29, 209, 161),
     8: (190, 140, 90),
     9: (255, 94, 98),
}

# ───────── scribbly helpers (toned-down jitter) ─────────
RNG = random.Random(77)

def jitter(p, j=0.7):
    return (p[0] + RNG.uniform(-j, j), p[1] + RNG.uniform(-j, j))

def scribble_line(surf, a, b, color=INK, width=2, passes=1, wiggle=0.5):
    for _ in range(passes):
        pygame.draw.line(surf, color, jitter(a, wiggle), jitter(b, wiggle), width)

def scribble_rect(surf, rect, color=INK, width=2, passes=1):
    x, y, w, h = rect
    scribble_line(surf, (x, y), (x+w, y), color, width, passes)
    scribble_line(surf, (x+w, y), (x+w, y+h), color, width, passes)
    scribble_line(surf, (x+w, y+h), (x, y+h), color, width, passes)
    scribble_line(surf, (x, y+h), (x, y), color, width, passes)

def draw_paper_bg():
    screen.fill(PAPER)
    # faint notebook lines
    for y in range(64, H-48, 42):
        scribble_line(screen, (24, y), (W-24, y), color=PALE, width=1, passes=1, wiggle=0.25)
    # soft border
    border = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.rect(border, (0, 0, 0, 28), (14, 14, W-28, H-28), width=6, border_radius=18)
    screen.blit(border, (0, 0))

# ───────── cute duck ─────────
jump_t = 0.0
jump_active = False

def trigger_jump():
    global jump_t, jump_active
    jump_t = 0.0
    jump_active = True

def duck_jump_offset(dt):
    global jump_t, jump_active
    if not jump_active:
        return 0.0
    jump_t += dt
    dur = 0.33
    t = min(jump_t / dur, 1.0)
    y = -24 * math.sin(t * math.pi)
    if t >= 1.0:
        jump_active = False
    return y

def draw_scribble_circle(surf, cx, cy, r, color=INK, passes=6):
    steps = 14
    pts = []
    for i in range(steps):
        ang = i/steps * math.tau
        pts.append(jitter((cx + math.cos(ang)*r, cy + math.sin(ang)*r), 0.8))
    for _ in range(passes):
        for i in range(steps):
            pygame.draw.line(surf, color, pts[i], pts[(i+1)%steps], 2)

def draw_duck(surf, x, y, dt, heading=1):
    y += math.sin(pygame.time.get_ticks() * 0.006) * 1.2
    y += duck_jump_offset(dt)
    # body + head
    draw_scribble_circle(surf, x, y, 16)
    draw_scribble_circle(surf, x + 18*heading, y - 5, 12)
    pygame.draw.circle(surf, INK, (int(x + 21*heading), int(y - 9)), 2)
    # beak
    beak = [(x+28*heading, y-6), (x+38*heading, y-2), (x+28*heading, y+2)]
    pygame.draw.polygon(surf, (255, 225, 140), beak)
    scribble_line(surf, beak[0], beak[1]); scribble_line(surf, beak[1], beak[2]); scribble_line(surf, beak[2], beak[0])
    # little legs
    scribble_line(surf, (x-6, y+16), (x-12, y+22))
    scribble_line(surf, (x+8, y+16), (x+14, y+22))

# ───────── state ─────────
grid = [-1 for _ in range(ROW_LEN)]  # one row
cursor = 0
duck_heading = 1

saved_rows = []  # each: {"cells": [...], "text": "digits without blanks"}
toast = "paint a row; press Enter to save"

def row_preview_text(cells):
    # digits string ignoring blanks
    digits = "".join(str(v) for v in cells if v >= 0)
    return digits if digits else "<empty>"

def add_current_row():
    global toast
    saved_rows.append({"cells": grid.copy(), "text": row_preview_text(grid)})
    toast = f"saved line {len(saved_rows)}"
    # clear for next line
    for i in range(ROW_LEN):
        grid[i] = -1

def load_saved_row_at(ix):
    if 0 <= ix < len(saved_rows):
        cells = saved_rows[ix]["cells"]
        for i in range(min(ROW_LEN, len(cells))):
            grid[i] = cells[i]
        for i in range(len(cells), ROW_LEN):
            grid[i] = -1

def cycle_here():
    v = grid[cursor]
    grid[cursor] = 0 if v == -1 else (v + 1) % 10
    trigger_jump()

def set_here(val):
    grid[cursor] = val
    trigger_jump()

def clear_row():
    for i in range(ROW_LEN):
        grid[i] = -1

# ───────── drawing ─────────
def draw_header():
    screen.blit(font.render("Duck Notebook — one line at a time", True, INK), (GRID_X, GRID_Y - 68))
    screen.blit(font_s.render("Space cycle • 0–9 set • Backspace blank • C clear • Enter save line • Click saved to load • Q quit", True, INK), (GRID_X, GRID_Y - 44))

def draw_row():
    for i in range(ROW_LEN):
        x = GRID_X + i * CELL
        y = GRID_Y
        rect = (x, y, CELL, CELL)
        pygame.draw.rect(screen, PALETTE[grid[i]], rect)
        pygame.draw.rect(screen, GRID_LINE, rect, 1)
        if grid[i] >= 0:
            idx = font_tiny.render(str(grid[i]), True, (60,60,70))
            screen.blit(idx, (x+3, y+2))
    # cursor outline only (so colour is visible immediately)
    cx = GRID_X + cursor * CELL
    scribble_rect(screen, (cx, GRID_Y, CELL, CELL), INK, 3, 1)

def draw_duck_at_cursor(dt):
    x = GRID_X + cursor * CELL + CELL//2 - 22
    y = GRID_Y - 72
    draw_duck(screen, x, y, dt, 1)

def draw_program_panel():
    # frame
    r = pygame.Rect(SAVED_X, SAVED_Y - 28, SAVED_W, H - (SAVED_Y - 28) - 40)
    pygame.draw.rect(screen, (255,255,255), r); scribble_rect(screen, r, INK, 2, 1)
    screen.blit(font.render("Program", True, INK), (SAVED_X + 10, SAVED_Y - 46))

    y = SAVED_Y
    mini = 16
    for i, row in enumerate(saved_rows):
        # colour mini row
        for c, v in enumerate(row["cells"][: int((SAVED_W - 20) / (mini + 2)) ]):
            cell = (SAVED_X + 8 + c * (mini + 2), y, mini, mini)
            pygame.draw.rect(screen, PALETTE[v], cell)
            pygame.draw.rect(screen, GRID_LINE, cell, 1)
        # text preview
        txt = font_tiny.render(row["text"], True, INK)
        screen.blit(txt, (SAVED_X + 8, y + mini + 4))
        # clickable rect
        row["_rect"] = pygame.Rect(SAVED_X + 4, y, SAVED_W - 12, mini + 22)
        y += mini + 30

    # toast
    screen.blit(font_s.render(toast, True, (60, 80, 140)), (SAVED_X + 10, r.bottom - 28))

# ───────── main loop ─────────
def main():
    global cursor, duck_heading, toast
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    running = False
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    cursor = max(0, cursor - 1); duck_heading = -1
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    cursor = min(ROW_LEN - 1, cursor + 1); duck_heading = 1
                elif e.key == pygame.K_SPACE:
                    cycle_here()
                elif e.key == pygame.K_BACKSPACE:
                    set_here(-1)
                elif e.key == pygame.K_c:
                    clear_row()
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    add_current_row(); toast = f"saved line {len(saved_rows)}"
                elif e.unicode and e.unicode.isdigit():
                    set_here(int(e.unicode))
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # click the row to move cursor
                if GRID_Y <= my < GRID_Y + CELL:
                    idx = (mx - GRID_X) // CELL
                    if 0 <= idx < ROW_LEN:
                        cursor = idx
                        # optional: cycle on click? uncomment if you want:
                        # cycle_here()
                # click saved line to load
                for i, row in enumerate(saved_rows):
                    r = row.get("_rect")
                    if r and r.collidepoint(mx, my):
                        load_saved_row_at(i)
                        toast = f"loaded line {i+1}"
                        break

        # draw everything
        draw_paper_bg()
        draw_header()
        draw_row()
        draw_duck_at_cursor(dt)
        draw_program_panel()
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
