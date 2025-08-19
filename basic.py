import pygame

# ---------------------------- CONFIG ----------------------------
TILE = 48

LEVEL = [
    "##################",
    "#@ . . . . . . R #",
    "#  O A B C D T S #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . . #",
    "#  . . . . . . K #",
    "##################",
]
GRID_H = len(LEVEL)
GRID_W = len(LEVEL[0])
assert all(len(r) == GRID_W for r in LEVEL), "LEVEL rows must match width"

SCREEN_W = GRID_W * TILE + 420
SCREEN_H = GRID_H * TILE
FPS = 60

# Instruction columns (edit these letters in the ascii map for clarity only)
COL_A = 2  # opcode
COL_B = 4  # dest register id (0=acc,1=a..4=d)
COL_C = 6  # immediate or register id depending on D
COL_D = 8  # flag (mode/output/halt)
PROGRAM_ROWS = range(3, GRID_H - 2)  # editable band

# Colors
COL_BG = (18, 18, 22)
COL_GRID = (36, 36, 44)
COL_TEXT = (235, 235, 245)
COL_HUD  = (28, 28, 34)
COL_WALL = (55, 55, 66)
COL_PLAYER = (255, 240, 150)
COL_CURSOR = (255, 255, 255)
COL_RUN = (0, 170, 140)
COL_STOP = (220, 140, 60)
COL_STEP = (120, 170, 240)
COL_CLR = (220, 60, 60)
COL_LABEL = (180, 180, 200)

# Palette 0..9
PALETTE = {
    0: (25, 25, 30),
    1: (74, 144, 226),
    2: (80, 227, 194),
    3: (255, 206, 84),
    4: (255, 107, 107),
    5: (162, 155, 254),
    6: (255, 159, 67),
    7: (29, 209, 161),
    8: (234, 181, 67),
    9: (255, 94, 98),
}

# ---------------------------- STATE ----------------------------
def tile_at(x, y):
    if 0 <= x < GRID_W and 0 <= y < GRID_H:
        return LEVEL[y][x]
    return "#"

def is_wall(x, y):
    return tile_at(x, y) == "#"

def find_spawn():
    for y,row in enumerate(LEVEL):
        for x,ch in enumerate(row):
            if ch == "@":
                return x, y
    return 1, 1

def make_color_grid():
    return [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]

# ---------------------------- INTERPRETER (streaming) ----------------------------
REG_BY_ID = {1:"a", 2:"b", 3:"c", 4:"d"}  # 0 => accumulator 'acc'

def build_program(grid):
    prog = []
    for y in PROGRAM_ROWS:
        A = grid[y][COL_A]
        B = grid[y][COL_B]
        C = grid[y][COL_C]
        D = grid[y][COL_D]
        prog.append((A,B,C,D))
    return prog

def src_value(C, D, regs):
    # D in {0,2}: immediate; D in {1,3}: register source (0 => acc)
    if D in (0,2):
        return C
    elif D in (1,3):
        if C == 0:
            return regs["acc"]
        name = REG_BY_ID.get(C)
        return regs.get(name, 0)
    return C

def get_dest_ref(B, regs):
    # returns (name_or_None, getter, setter)
    if B == 0:
        return None, (lambda: regs["acc"]), (lambda v: regs.__setitem__("acc", v))
    name = REG_BY_ID.get(B)
    if not name:
        return None, (lambda: 0), (lambda v: None)
    return name, (lambda: regs[name]), (lambda v: regs.__setitem__(name, v))

def out_if_flag(D, B, regs, out):
    if D in (2,3):
        if B == 0:
            out.append(regs["acc"])
        else:
            name = REG_BY_ID.get(B)
            if name: out.append(regs[name])

def interpret_stream(grid):
    """
    Generator that yields trace lines as it executes.
    Yields tuples: (ip_1_based, text_line, out_snapshot, regs_snapshot, halted_bool)
    """
    program = build_program(grid)
    ip = 0
    regs = {"acc":0, "a":0, "b":0, "c":0, "d":0}
    out = []
    safety = 200

    while 0 <= ip < len(program) and safety > 0:
        safety -= 1
        A,B,C,D = program[ip]
        # empty / NOP row
        if A == 0:
            text = f"@{ip+1}: NOP"
            yield (ip+1, text, list(out), dict(regs), False)
            ip += 1
            continue

        # compute SRC & destination helpers
        SRC = src_value(C, D, regs)
        name, get, setv = get_dest_ref(B, regs)

        halted = False
        pretty_dst = "acc" if B == 0 else (name if name else f"R?{B}")
        pretty_src = f"#{SRC}" if D in (0,2) else ( "acc" if (D in (1,3) and C==0) else f"R{C}" )

        # Execute
        if A == 1:  # SET
            setv(SRC)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: SET {pretty_dst} = {pretty_src}"

            if D == 9: halted = True
            ip += 1

        elif A == 2:  # ADD
            setv(get() + SRC)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: ADD {pretty_dst} += {pretty_src}"
            if D == 9: halted = True
            ip += 1

        elif A == 3:  # SUB
            setv(get() - SRC)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: SUB {pretty_dst} -= {pretty_src}"
            if D == 9: halted = True
            ip += 1

        elif A == 4:  # MUL
            setv(get() * SRC)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: MUL {pretty_dst} *= {pretty_src}"
            if D == 9: halted = True
            ip += 1

        elif A == 5:  # DIV
            d = max(1, SRC)
            setv(get() // d)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: DIV {pretty_dst} //= {d}"
            if D == 9: halted = True
            ip += 1

        elif A == 6:  # JNZ
            cond = (get() != 0)
            dest = SRC - 1
            text = f"@{ip+1}: JNZ {pretty_dst}? {cond} → {SRC if cond else ip+2}"
            if cond and 0 <= dest < len(program):
                ip = dest
            else:
                ip += 1
            if D == 9: halted = True

        elif A == 7:  # OUT
            out.append(get())
            text = f"@{ip+1}: OUT {pretty_dst} = {get()}"
            if D == 9: halted = True
            ip += 1

        elif A == 8:  # CLR
            setv(0)
            out_if_flag(D, B, regs, out)
            text = f"@{ip+1}: CLR {pretty_dst}"
            if D == 9: halted = True
            ip += 1

        elif A == 9:  # END
            text = f"@{ip+1}: END"
            halted = True
            ip = len(program)  # break after yield

        else:
            text = f"@{ip+1}: UNKNOWN A={A}; skipping"
            ip += 1

        yield (ip if not halted else ip, text, list(out), dict(regs), halted)

    if safety == 0:
        yield (None, "! safety stop (possible infinite loop)", list(out), dict(regs), True)

# ---------------------------- PYGAME SETUP ----------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("DuckLang — Color Grid Interpreter (Streaming)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)
font_small = pygame.font.SysFont("consolas", 14)

px, py = find_spawn()
grid = make_color_grid()

# run control
runner = None
tick_div = 4  # run one instruction every 4 frames

# HUD log
log_lines = [
    "Space: cycle digit color 0..9",
    "Step on RUN to start, STEP to single-step, STOP to halt, CLR to clear grid."
]

def add_log(msg):
    log_lines.append(msg)
    if len(log_lines) > 240:
        del log_lines[:80]

# ---------------------------- DRAWING ----------------------------
def draw_world():
    screen.fill(COL_BG, (0, 0, GRID_W * TILE, SCREEN_H))
    for y in range(GRID_H):
        for x in range(GRID_W):
            rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            ch = LEVEL[y][x]
            if ch == "#":
                pygame.draw.rect(screen, COL_WALL, rect)
            else:
                # paintable cells get color; walls use wall color
                color = PALETTE[grid[y][x]] if ch != " " else COL_WALL
                pygame.draw.rect(screen, color, rect)

            # overlays / labels
            label = None
            if ch == "R": label, col = "RUN", COL_RUN
            elif ch == "S": label, col = "STOP", COL_STOP
            elif ch == "T": label, col = "STEP", COL_STEP
            elif ch == "K": label, col = "CLR", COL_CLR
            elif ch in ("O","A","B","C","D"):
                label, col = ch, COL_LABEL
            else:
                col = None

            pygame.draw.rect(screen, COL_GRID, rect, 1)
            if label:
                pygame.draw.rect(screen, col, rect, 2)
                txt = font_small.render(label, True, COL_TEXT)
                screen.blit(txt, (rect.x + TILE//2 - txt.get_width()//2,
                                  rect.y + TILE//2 - txt.get_height()//2))

def draw_player():
    r = pygame.Rect(px * TILE + 6, py * TILE + 6, TILE - 12, TILE - 12)
    pygame.draw.ellipse(screen, COL_PLAYER, r)
    pygame.draw.rect(screen, COL_CURSOR, (px * TILE, py * TILE, TILE, TILE), 2)

def draw_hud():
    hud = pygame.Rect(GRID_W * TILE, 0, SCREEN_W - GRID_W * TILE, SCREEN_H)
    pygame.draw.rect(screen, COL_HUD, hud)
    screen.blit(font.render("DuckLang — Color Grid Interpreter", True, COL_TEXT), (hud.x + 12, 10))

    # Legend
    y = 44
    for line in [
        f"Cols: A@{COL_A}  B@{COL_B}  C@{COL_C}  D@{COL_D}",
        "B=0→acc, 1=a,2=b,3=c,4=d",
        "D: 0 imm, 1 reg, 2 imm+OUT, 3 reg+OUT, 9 HALT",
        "A: 1 SET 2 ADD 3 SUB 4 MUL 5 DIV 6 JNZ 7 OUT 8 CLR 9 END",
        "",
    ]:
        screen.blit(font_small.render(line, True, COL_TEXT), (hud.x + 12, y)); y += 18

    # Log
    screen.blit(font.render("Trace / Output:", True, COL_TEXT), (hud.x + 12, y+4))
    y += 30
    wrap_w = hud.width - 24
    for ln in log_lines[-22:]:
        for part in wrap_text(ln, font_small, wrap_w):
            screen.blit(font_small.render(part, True, COL_TEXT), (hud.x + 12, y))
            y += 18

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

# ---------------------------- INPUT / LOGIC ----------------------------
def try_move(dx, dy):
    global px, py, runner
    nx, ny = px + dx, py + dy
    if is_wall(nx, ny):
        return
    px, py = nx, ny

    ch = LEVEL[ny][nx]
    if ch == "R":
        start_run()
    elif ch == "S":
        stop_run()
    elif ch == "T":
        step_once()
    elif ch == "K":
        clear_grid()
    else:
        # paintable cell? cycle
        if LEVEL[ny][nx] != "#":
            grid[ny][nx] = (grid[ny][nx] + 1) % 10

def clear_grid():
    for y in range(GRID_H):
        for x in range(GRID_W):
            if LEVEL[y][x] != "#":
                grid[y][x] = 0
    add_log("— Cleared grid.")

def start_run():
    global runner
    runner = interpret_stream(grid)
    add_log("— RUN started.")

def stop_run():
    global runner
    runner = None
    add_log("— RUN stopped.")

def step_once():
    global runner
    if runner is None:
        runner = interpret_stream(grid)
    try:
        ip1, line, out, regs, halted = next(runner)
        add_log(f"{line}")
        if out:
            add_log(f"OUT: {out}")
        add_log(f"REGS: acc={regs['acc']} a={regs['a']} b={regs['b']} c={regs['c']} d={regs['d']}")
        if halted:
            runner = None
            add_log("— HALT.")
    except StopIteration:
        runner = None
        add_log("— HALT.")

# ---------------------------- MAIN LOOP ----------------------------
def main():
    global runner
    frame = 0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    try_move(-1, 0)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    try_move(1, 0)
                elif e.key in (pygame.K_UP, pygame.K_w):
                    try_move(0, -1)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    try_move(0, 1)
                elif e.key == pygame.K_SPACE:
                    # cycle current cell
                    if LEVEL[py][px] != "#":
                        grid[py][px] = (grid[py][px] + 1) % 10
                elif e.key == pygame.K_r:
                    # reset to spawn
                    global px, py
                    px, py = find_spawn()

        # streaming run tick
        if runner is not None:
            frame += 1
            if frame % tick_div == 0:
                step_once()

        draw_world()
        draw_player()
        draw_hud()
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()
