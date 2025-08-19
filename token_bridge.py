# duck_colors_frontend.py
# Cute, scribbly duck frontend for the COLOUR GRAMMAR that feeds YOUR language.
# Fixes based on your feedback:
#  - Space shows colour immediately (cursor is outline only).
#  - Operators via colours work (ESC = 9,9 then code colour).
#  - Clearer status text; duck no longer covers headings.
#  - Live "triplet" hint for the last 3 colours (helps with ESC).
#  - Program panel on the right: Enter to add line, click to load, S to save all.
#
# IMPORTANT: change the import below to your module that defines run(fn, text).

import math, random, time, json, os, pygame
global last_ok, last_msg
last_ok = True
last_msg = "Paint colours to evaluate…"

# ───────────── 1) IMPORT YOUR LANGUAGE ─────────────
FALLBACK_IMPORT = False
try:
    # ⬇️ CHANGE THIS if your module is not named "basic"
    from basic import run
except Exception as import_error:
    FALLBACK_IMPORT = True
    def run(fn, text):
        # Fallback only to show a clear warning in the HUD.
        class FakeErr:
            def as_string(self):
                return f"[IMPORT ERROR] Edit duck_colors_frontend.py to import your module. Details: {import_error}"
        return None, FakeErr()

# ───────────── 2) WINDOW / LOOK ─────────────
W, H = 1280, 760
FPS = 60
RNG = random.Random(77)

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Colour‑Duck — live (uses your language)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Comic Sans MS", 22)
font_s = pygame.font.SysFont("Comic Sans MS", 16)
font_tiny = pygame.font.SysFont("Comic Sans MS", 12)

PAPER  = (245, 242, 236)
INK    = (40, 42, 46)
PALE   = (220, 220, 228)
HILITE = (255, 225, 140)
OKCOL  = (40, 120, 60)
ERRCOL = (180, 50, 50)
WARN   = (200, 120, 30)
GRID_LINE = (180, 180, 188)

PALETTE = {
    -1: (245, 242, 236),    # blank / paper
     0: (230, 232, 235),    # 0
     1: (74, 144, 226),     # 1
     2: (80, 227, 194),     # 2
     3: (255, 206, 84),     # 3
     4: (255, 140, 120),    # 4
     5: (162, 155, 254),    # 5
     6: (255, 159, 67),     # 6
     7: (29, 209, 161),     # 7
     8: (190, 140, 90),     # 8
     9: (255, 94, 98),      # 9 (ESC marker)
}

# ───────────── 3) SCRIBBLY HELPERS & DUCK (lower jitter) ─────────────
def jitter(p, j=0.7):
    return (p[0]+RNG.uniform(-j,j), p[1]+RNG.uniform(-j,j))

def scribble_line(surf, a, b, color=INK, width=2, passes=1, wiggle=0.6):
    for _ in range(passes):
        pygame.draw.line(surf, color, jitter(a, wiggle), jitter(b, wiggle), width)

def scribble_rect(surf, rect, color=INK, width=2, passes=1):
    x,y,w,h = rect
    scribble_line(surf, (x, y), (x+w, y), color, width, passes)
    scribble_line(surf, (x+w, y), (x+w, y+h), color, width, passes)
    scribble_line(surf, (x+w, y+h), (x, y+h), color, width, passes)
    scribble_line(surf, (x, y+h), (x, y), color, width, passes)

def draw_paper_bg():
    screen.fill(PAPER)
    for y in range(64, H-48, 42):
        scribble_line(screen, (24, y), (W-24, y), color=PALE, width=1, passes=1, wiggle=0.25)
    border = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.rect(border, (0,0,0,28), (14,14,W-28,H-28), width=6, border_radius=18)
    screen.blit(border, (0,0))

def draw_scribble_circle(surf, cx, cy, r, color=INK, passes=6):
    steps = 14
    pts = []
    for i in range(steps):
        ang = i/steps * math.tau
        pts.append(jitter((cx + math.cos(ang)*r, cy + math.sin(ang)*r), 0.8))
    for _ in range(passes):
        for i in range(steps):
            pygame.draw.line(surf, color, pts[i], pts[(i+1)%steps], 2)

# hop animation
jump_t = 0.0
jump_active = False
def trigger_jump():
    global jump_t, jump_active
    jump_t = 0.0
    jump_active = True
def duck_jump_offset(dt):
    global jump_t, jump_active
    if not jump_active: return 0.0
    jump_t += dt
    dur = 0.33
    t = min(jump_t / dur, 1.0)
    y = -24 * math.sin(t*math.pi)
    if t >= 1.0: jump_active = False
    return y

def draw_duck(surf, x, y, dt, heading=1):
    y += math.sin(pygame.time.get_ticks()*0.006)*1.2
    y += duck_jump_offset(dt)
    draw_scribble_circle(surf, x, y, 16)
    draw_scribble_circle(surf, x + 18*heading, y - 5, 12)
    pygame.draw.circle(surf, INK, (int(x + 21*heading), int(y - 9)), 2)
    beak = [(x+28*heading, y-6), (x+38*heading, y-2), (x+28*heading, y+2)]
    pygame.draw.polygon(surf, (255, 225, 140), beak)
    scribble_line(surf, beak[0], beak[1]); scribble_line(surf, beak[1], beak[2]); scribble_line(surf, beak[2], beak[0])
    scribble_line(surf, (x-6,y+16), (x-12,y+22)); scribble_line(surf, (x+8,y+16), (x+14,y+22))

# ───────────── 4) GRID (one editable row) ─────────────
CELL = 42
ROW_LEN = 48
GRID_X = 60
GRID_Y = 160
grid = [-1 for _ in range(ROW_LEN)]
cursor = 0
duck_heading = 1

# program panel (saved lines)
SAVED_X = GRID_X + ROW_LEN*CELL + 60
SAVED_Y = GRID_Y
SAVED_W = 360
SAVED_CELL = 18
saved_lines = []  # list of dicts: {"cells":[...], "source":str, "value":optional}

# ───────────── 5) DECODER (colours → tokens → source) ─────────────
ESC_TOKEN = {0:"+",1:"-",2:"*",3:"/",4:"^",5:"(",6:")",7:"=",8:"VAR"}
IDENT_MAP = {0:"a",1:"b",2:"c",3:"d",4:"x",5:"y"}

def decode_to_tokens(cells):
    tokens = []
    i = 0
    n = len(cells)
    def is_blank(v): return v == -1
    def starts_ESC(idx): return idx+1 < n and cells[idx] == 9 and cells[idx+1] == 9
    while i < n:
        if is_blank(cells[i]): i += 1; continue
        if starts_ESC(i):
            i += 2
            if i >= n: return [], "Invalid Syntax: ESC at end of line"
            code = cells[i]; i += 1
            if code == 9:
                if i >= n: return [], "Invalid Syntax: truncated identifier after ESC C9"
                ident_code = cells[i]; i += 1
                name = IDENT_MAP.get(ident_code)
                if not name: return [], f"Invalid Syntax: unknown identifier colour C{ident_code}"
                tokens.append(name)
            else:
                tok = ESC_TOKEN.get(code)
                if not tok: return [], f"Invalid Syntax: unknown ESC colour C{code}"
                tokens.append(tok)
            continue
        # number run
        j = i
        while j < n and not is_blank(cells[j]) and not starts_ESC(j) and (0 <= cells[j] <= 9):
            j += 1
        if j == i: return [], f"Invalid Syntax near cell {i}"
        digits = [str(cells[k]) for k in range(i, j)]
        tokens.append("".join(digits))
        i = j
    return tokens, None

def tokens_to_source(tokens):
    return " ".join(tokens)

# ───────────── 6) LIVE EVAL ─────────────

last_src = "<empty>"

last_val = None
_last_eval_at = 0.0

def evaluate_now(force=False):
    global last_src,  last_val, _last_eval_at
    now = time.time()
    if not force and (now - _last_eval_at) < 0.06: return
    _last_eval_at = now
    tokens, err = decode_to_tokens(grid)
    if err:
        last_src = "<invalid>"
        last_ok = False
        last_msg = err
        last_val = None
        return
    src = tokens_to_source(tokens)
    last_src = src if src else "<empty>"
    if not src:
        last_ok = True; last_msg = "Paint colours to evaluate…"; last_val = None; return
    value, lang_err = run("<duck>", src)
    if lang_err:
        try: msg = lang_err.as_string()
        except Exception: msg = str(lang_err)
        last_ok = False; last_msg = msg.splitlines()[0]; last_val = None
    else:
        last_ok = True; last_val = value; last_msg = f"{src}  =>  {value}"

# ───────────── 7) EDITING ─────────────
recent_paints = []  # keep last 3 colour indices for ESC hint

def cycle_here():
    v = grid[cursor]
    if v == -1: grid[cursor] = 0
    else:
        grid[cursor] = v + 1
        if grid[cursor] > 9: grid[cursor] = -1
    push_paint_hint(grid[cursor])
    trigger_jump()
    evaluate_now()

def set_here(val):
    grid[cursor] = val
    push_paint_hint(val)
    evaluate_now()

def push_paint_hint(v):
    if v < -1: return
    if v == -1: return
    recent_paints.append(v)
    if len(recent_paints) > 3: recent_paints.pop(0)

def clear_row():
    for i in range(ROW_LEN): grid[i] = -1
    recent_paints.clear()
    evaluate_now(force=True)

# save/load lines
def add_current_line():
    tokens, err = decode_to_tokens(grid)
    if err: return False, err
    src = tokens_to_source(tokens)
    value, lang_err = run("<duck>", src) if src else (None, None)
    saved_lines.append({"cells": grid.copy(), "source": src, "value": None if lang_err else value})
    return True, None

def export_saved(path_txt="program_lines.txt", path_json="program_lines.json"):
    with open(path_txt, "w", encoding="utf-8") as f:
        for i, ln in enumerate(saved_lines, 1):
            f.write(ln["source"] + ("\n" if i < len(saved_lines) else ""))
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(saved_lines, f, indent=2)
    return os.path.abspath(path_txt), os.path.abspath(path_json)

def load_saved_line_at(ix):
    if 0 <= ix < len(saved_lines):
        cells = saved_lines[ix]["cells"]
        for i in range(min(ROW_LEN, len(cells))):
            grid[i] = cells[i]
        for i in range(len(cells), ROW_LEN):
            grid[i] = -1
        evaluate_now(force=True)

# ───────────── 8) DRAWING ─────────────
def draw_header():
    screen.blit(font.render("Paint a single line of colours", True, INK), (GRID_X, GRID_Y-68))
    screen.blit(font_s.render("Digits = colours (0..9).  ESC = Red Red.  After ESC: C0:+ C1:- C2:* C3:/ C4:^ C5:( C6:) C7:= C8:VAR C9:IDENT→(0:a 1:b 2:c 3:d 4:x 5:y)", True, INK), (GRID_X, GRID_Y-44))

def draw_grid():
    # cells
    for i in range(ROW_LEN):
        x = GRID_X + i*CELL; y = GRID_Y
        rect = (x, y, CELL, CELL)
        pygame.draw.rect(screen, PALETTE[grid[i]], rect)
        pygame.draw.rect(screen, GRID_LINE, rect, 1)
        if grid[i] >= 0:
            idx = font_tiny.render(str(grid[i]), True, (60,60,70))
            screen.blit(idx, (x+3, y+2))
    # cursor (outline only → you see the colour underneath)
    cx = GRID_X + cursor*CELL
    scribble_rect(screen, (cx, GRID_Y, CELL, CELL), INK, 3, 1)
    # ESC triplet hint
    hint = " ".join(str(v) for v in recent_paints[-3:])
    if hint:
        screen.blit(font_s.render(f"Last 3: {hint}  (ESC is 9 9 …)", True, INK), (GRID_X, GRID_Y + CELL + 8))

def draw_duck_at_cursor(dt):
    x = GRID_X + cursor*CELL + CELL//2 - 22
    y = GRID_Y - 72  # moved higher so it won't cover text
    draw_duck(screen, x, y, dt, 1)

def draw_status_panel():
    bx = GRID_X
    by = GRID_Y + CELL + 42
    bw = (SAVED_X - 30) - bx
    box = pygame.Rect(bx, by, bw, 180)
    pygame.draw.rect(screen, (255,255,255), box); scribble_rect(screen, box, INK, 2, 1)
    title = "✅ Live value" if last_ok and last_val is not None else ("ℹ️ Status" if last_ok else "❌ Error")
    screen.blit(font.render(title, True, INK), (bx+10, by-18))
    # import warning
    if FALLBACK_IMPORT:
        screen.blit(font_s.render("WARNING: edit import at top to use your interpreter.", True, WARN), (bx+10, by+8))
    # source
    src_line = last_src if last_src else "<empty>"
    screen.blit(font_s.render(f"Source: {src_line[:90]}{'…' if len(src_line)>90 else ''}", True, INK), (bx+10, by+32))
    # message/value
    msg = last_msg
    col = OKCOL if last_ok else ERRCOL
    y = by + 56
    for line in wrap_text(msg, font_s, bw-20):
        screen.blit(font_s.render(line, True, col), (bx+10, y)); y += 20
    # controls
    y += 6
    for ln in [
        "←/→ move   Space cycle   Backspace blank   C clear",
        "Enter add line   Click a saved line to load   S save all   Q quit",
        "Place '+': 9 9 0     Place 'x': 9 9 9 4",
    ]:
        screen.blit(font_s.render(ln, True, INK), (bx+10, y)); y += 18

def draw_saved_panel():
    # frame
    r = pygame.Rect(SAVED_X, SAVED_Y-28, SAVED_W, H - (SAVED_Y-28) - 40)
    pygame.draw.rect(screen, (255,255,255), r); scribble_rect(screen, r, INK, 2, 1)
    screen.blit(font.render("Program", True, INK), (SAVED_X + 10, SAVED_Y - 46))
    # lines
    y = SAVED_Y - 4
    for i, ln in enumerate(saved_lines):
        # miniature colour cells
        mini_w = min(len(ln["cells"]), 24)
        for c in range(mini_w):
            cell_rect = (SAVED_X + 8 + c*(SAVED_CELL+2), y, SAVED_CELL, SAVED_CELL)
            col = PALETTE[ln["cells"][c]]
            pygame.draw.rect(screen, col, cell_rect); pygame.draw.rect(screen, GRID_LINE, cell_rect, 1)
        # source preview
        src = ln["source"]
        src_txt = font_tiny.render(src[:26] + ("…" if len(src)>26 else ""), True, INK)
        screen.blit(src_txt, (SAVED_X + 8, y + SAVED_CELL + 4))
        # clickable area extent
        ln["_rect"] = pygame.Rect(SAVED_X + 4, y, SAVED_W - 12, SAVED_CELL + 22)
        # step
        y += SAVED_CELL + 34
    # save hint
    screen.blit(font_s.render("Press S to save all lines (text + json).", True, INK), (SAVED_X + 8, r.bottom - 28))

def wrap_text(text, fnt, max_w):
    words, line = text.split(" "), ""
    out = []
    for w in words:
        test = (line + " " + w) if line else w
        if fnt.size(test)[0] <= max_w:
            line = test
        else:
            out.append(line); line = w
    if line: out.append(line)
    return out

# ───────────── 9) MAIN LOOP ─────────────
def main():
    global cursor, duck_heading
    running = True
    evaluate_now(force=True)

    while running:
        dt = clock.tick(FPS)/1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    running = False
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    cursor = max(0, cursor-1); duck_heading = -1
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    cursor = min(ROW_LEN-1, cursor+1); duck_heading = 1
                elif e.key == pygame.K_SPACE:
                    cycle_here()
                elif e.key == pygame.K_BACKSPACE:
                    set_here(-1)
                elif e.key == pygame.K_c:
                    clear_row()
                elif e.key == pygame.K_RETURN:
                    ok, err = add_current_line()
                    if not ok:
                        # brief error flash in status
                        last_ok = False; last_msg = err
                elif e.key == pygame.K_s:
                    txt, js = export_saved()
                    last_ok = True; last_msg = f"Saved {len(saved_lines)} line(s) → {txt} & {js}"
                # optional: number keys set exact colour
                elif e.unicode in "0123456789":
                    set_here(int(e.unicode))
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # click on the row → move + cycle
                if GRID_Y <= my < GRID_Y + CELL:
                    idx = (mx - GRID_X) // CELL
                    if 0 <= idx < ROW_LEN:
                        cursor = idx; cycle_here()
                # click a saved line to load
                for i, ln in enumerate(saved_lines):
                    r = ln.get("_rect")
                    if r and r.collidepoint(mx, my):
                        load_saved_line_at(i)
                        break

        # draw
        draw_paper_bg()
        draw_header()
        draw_grid()
        draw_duck_at_cursor(dt)
        draw_status_panel()
        draw_saved_panel()
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
