# duck_notebook.py
# Cute scribbly notebook with a duck.
# - One editable row of "colours as digits"
# - Space cycles blank→0→1→…→9→blank
# - Number keys 0–9 set the cell directly
# - ← / → moves the cursor
# - Backspace blanks the cell
# - C clears row
# - Enter saves the row into Program panel (right)
# - Click a saved row to reload
# - R runs all saved rows through basic.py
# - S saves to duck_programs/<timestamp>.duck
# - O loads the most-recent .duck from duck_programs/ (reconstructs colours)
# - Q quits

import os, datetime
import pygame, math, random
from basic import run   # your interpreter: run(fn, src) -> (value, err)

# ───────── window / layout ─────────
W, H = 1280, 740
FPS = 60

CELL = 36
ROW_LEN = 24
GRID_X = 40
GRID_Y = 200

GAP = 24
SAVED_X = GRID_X + ROW_LEN * CELL + GAP
SAVED_W = 320
SAVED_Y = GRID_Y - 24

# ───────── export folder ─────────
EXPORT_DIR = "duck_programs"
os.makedirs(EXPORT_DIR, exist_ok=True)

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Duck Notebook — colour grammar")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Comic Sans MS", 22)
font_s = pygame.font.SysFont("Comic Sans MS", 16)
font_tiny = pygame.font.SysFont("Comic Sans MS", 12)

# ───────── palette ─────────
PAPER  = (245, 242, 236)
INK    = (40, 42, 46)
PALE   = (220, 220, 228)
GRID_LINE = (185, 185, 192)

PALETTE = {
    -1: PAPER,
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

# ───────── scribbly helpers ─────────
RNG = random.Random(77)
def jitter(p, j=0.7): return (p[0]+RNG.uniform(-j,j), p[1]+RNG.uniform(-j,j))
def scribble_line(surf,a,b,color=INK,width=2,passes=1,w=0.5):
    for _ in range(passes): pygame.draw.line(surf,color,jitter(a,w),jitter(b,w),width)
def scribble_rect(surf,rect,color=INK,width=2,passes=1):
    x,y,w,h=rect
    scribble_line(surf,(x,y),(x+w,y),color,width,passes)
    scribble_line(surf,(x+w,y),(x+w,y+h),color,width,passes)
    scribble_line(surf,(x+w,y+h),(x,y+h),color,width,passes)
    scribble_line(surf,(x,y+h),(x,y),color,width,passes)

def draw_paper_bg():
    screen.fill(PAPER)
    for y in range(64,H-48,42): scribble_line(screen,(24,y),(W-24,y),PALE,1,1,0.25)
    border=pygame.Surface((W,H),pygame.SRCALPHA)
    pygame.draw.rect(border,(0,0,0,28),(14,14,W-28,H-28),6,18)
    screen.blit(border,(0,0))

# ───────── duck ─────────
jump_t, jump_active = 0.0, False
def trigger_jump(): 
    global jump_t,jump_active; jump_t=0;jump_active=True
def duck_jump_offset(dt):
    global jump_t,jump_active
    if not jump_active: return 0
    jump_t+=dt; dur=0.33; t=min(jump_t/dur,1.0); y=-24*math.sin(t*math.pi)
    if t>=1: jump_active=False
    return y
def draw_scribble_circle(surf,cx,cy,r,color=INK,passes=6):
    steps=14; pts=[jitter((cx+math.cos(i/steps*math.tau)*r,cy+math.sin(i/steps*math.tau)*r),0.8) for i in range(steps)]
    for _ in range(passes):
        for i in range(steps): pygame.draw.line(surf,color,pts[i],pts[(i+1)%steps],2)
def draw_duck(surf,x,y,dt,heading=1):
    y+=math.sin(pygame.time.get_ticks()*0.006)*1.2
    y+=duck_jump_offset(dt)
    draw_scribble_circle(surf,x,y,16)
    draw_scribble_circle(surf,x+18*heading,y-5,12)
    pygame.draw.circle(surf,INK,(int(x+21*heading),int(y-9)),2)
    beak=[(x+28*heading,y-6),(x+38*heading,y-2),(x+28*heading,y+2)]
    pygame.draw.polygon(surf,(255,225,140),beak)
    scribble_line(surf,beak[0],beak[1]); scribble_line(surf,beak[1],beak[2]); scribble_line(surf,beak[2],beak[0])
    scribble_line(surf,(x-6,y+16),(x-12,y+22)); scribble_line(surf,(x+8,y+16),(x+14,y+22))

# ───────── colour grammar ─────────
# doubles → tokens
OP_BY_DOUBLE = {1:"+",2:"-",3:"*",4:"/",5:"^",6:"(",7:")",8:"=",9:"VAR"}
# 9 + digit → identifier
IDENT_BY_PAIR = {1:"a",2:"b",3:"c",4:"d",5:"e",6:"f",7:"g",8:"h",9:None}
# inverse (for loading .duck back into coloured cells)
DOUBLE_BY_OP = {"+":1, "-":2, "*":3, "/":4, "^":5, "(":6, ")":7, "=":8}
IDENT_TO_DIGIT = {v:k for k,v in IDENT_BY_PAIR.items() if v}

def tokenize_cells_to_source(cells):
    """Encode a row of colour cells into source using the colour grammar."""
    src=[]; i=0; buf=[]
    def flush(): 
        nonlocal buf
        if buf: src.append("".join(buf)); buf=[]
    while i<len(cells):
        v=cells[i]; nxt=cells[i+1] if i+1<len(cells) else None
        if v==-1: flush(); i+=1; continue
        if v==9 and nxt==9: flush(); src.append("VAR"); i+=2; continue
        if nxt is not None and v==nxt and v in OP_BY_DOUBLE: flush(); src.append(OP_BY_DOUBLE[v]); i+=2; continue
        if v==9 and nxt in IDENT_BY_PAIR and IDENT_BY_PAIR[nxt]: flush(); src.append(IDENT_BY_PAIR[nxt]); i+=2; continue
        buf.append(str(v)); i+=1
    flush(); return " ".join(src).strip()

def encode_line_to_cells(line, width=ROW_LEN):
    """
    Convert a plain source line (from .duck) back into a colour row.
    We keep it simple: tokens are digits, single-letter ids a–h, VAR, and ops + - * / ^ ( ) =
    """
    cells=[]
    i=0
    line=line.strip()
    while i < len(line) and len(cells) < width:
        ch=line[i]

        # whitespace
        if ch.isspace(): i+=1; continue

        # operators
        if ch in DOUBLE_BY_OP:
            col=DOUBLE_BY_OP[ch]
            cells.extend([col,col])
            i+=1
            continue

        # parenthesis/operators already covered; numbers
        if ch.isdigit():
            # read a whole number
            j=i
            while j<len(line) and line[j].isdigit(): j+=1
            for d in line[i:j]:
                cells.append(int(d))
            i=j
            continue

        # identifiers (single-letter a..h)
        if ch.isalpha():
            # read word
            j=i
            while j<len(line) and line[j].isalpha(): j+=1
            word=line[i:j]
            if word=="VAR":
                cells.extend([9,9])
            else:
                # take first character; if it's a..h, map to 9 + digit
                c=word[0].lower()
                if c in IDENT_TO_DIGIT:
                    cells.extend([9, IDENT_TO_DIGIT[c]])
                else:
                    # unknown ident → we’ll just ignore (or you can place blanks)
                    pass
            i=j
            continue

        # anything else → skip
        i+=1

    # pad to width with blanks
    if len(cells) < width:
        cells.extend([-1]*(width-len(cells)))
    else:
        cells=cells[:width]
    return cells

# ───────── state ─────────
grid=[-1]*ROW_LEN; cursor=0; duck_heading=1
saved_rows=[]; toast="paint a row; press Enter to save"; output_lines=[]

def program_source():
    return "\n".join(r["text"] for r in saved_rows if r["text"])

def add_current_row():
    global toast
    text=tokenize_cells_to_source(grid)
    saved_rows.append({"cells":grid.copy(),"text":text})
    toast=f"saved line {len(saved_rows)}"
    for i in range(ROW_LEN): grid[i]=-1

def load_saved_row_at(ix):
    if 0<=ix<len(saved_rows):
        for i,v in enumerate(saved_rows[ix]["cells"]): 
            if i<ROW_LEN: grid[i]=v

def cycle_here(): 
    global grid; v=grid[cursor]; grid[cursor]=0 if v==-1 else (v+1)%10; trigger_jump()
def set_here(val): grid[cursor]=val; trigger_jump()
def clear_row(): 
    global grid; grid=[-1]*ROW_LEN

def run_program():
    global toast,output_lines
    src=program_source()
    if not src.strip(): toast="no program"; return
    value,err=run("<duck>",src)
    if err:
        msg=getattr(err,"as_string",lambda: str(err))()
    else:
        msg=str(value)
    output_lines.append(msg); toast="ran program"

def save_duck():
    """Save current program as a .duck file into EXPORT_DIR with timestamp."""
    global toast
    src=program_source()
    if not src.strip():
        toast="nothing to save"
        return
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname=f"{ts}.duck"
    path=os.path.join(EXPORT_DIR,fname)
    try:
        with open(path,"w",encoding="utf-8") as f:
            f.write(src+"\n")
        toast=f"saved {os.path.join(EXPORT_DIR,fname)}"
        output_lines.append(f"saved → {path}")
    except Exception as e:
        toast=f"save error: {e}"

def load_latest_duck():
    """Load the most recent .duck from EXPORT_DIR and rebuild coloured rows."""
    global toast, saved_rows
    try:
        files=[f for f in os.listdir(EXPORT_DIR) if f.lower().endswith(".duck")]
        if not files:
            toast="no .duck files"
            return
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(EXPORT_DIR,fn)), reverse=True)
        path=os.path.join(EXPORT_DIR, files[0])
        with open(path,"r",encoding="utf-8") as f:
            lines=[ln.rstrip("\n") for ln in f.readlines()]
        # rebuild saved_rows
        saved_rows.clear()
        for ln in lines:
            if not ln.strip(): 
                continue
            cells=encode_line_to_cells(ln, width=ROW_LEN)
            saved_rows.append({"cells":cells, "text":ln})
        toast=f"loaded {files[0]} ({len(saved_rows)} lines)"
        output_lines.append(f"loaded ← {path}")
    except Exception as e:
        toast=f"load error: {e}"

# ───────── drawing ─────────
def draw_header():
    screen.blit(font.render("Duck Notebook — colour grammar",True,INK),(GRID_X,GRID_Y-68))
    screen.blit(
        font_s.render(
            "Space cycle • 0–9 set • Backspace blank • C clear • Enter save • Click saved to load • R run • S save .duck • O load latest • Q quit",
            True, INK),
        (GRID_X,GRID_Y-44)
    )

def draw_row():
    for i,v in enumerate(grid):
        x=GRID_X+i*CELL; rect=(x,GRID_Y,CELL,CELL)
        pygame.draw.rect(screen,PALETTE[v],rect)
        pygame.draw.rect(screen,GRID_LINE,rect,1)
        if v>=0: screen.blit(font_tiny.render(str(v),True,(60,60,70)),(x+3,GRID_Y+2))
    scribble_rect(screen,(GRID_X+cursor*CELL,GRID_Y,CELL,CELL),INK,3,1)

def draw_duck_at_cursor(dt):
    x=GRID_X+cursor*CELL+CELL//2-22; y=GRID_Y-72; draw_duck(screen,x,y,dt,1)

def draw_program_panel():
    r=pygame.Rect(SAVED_X,SAVED_Y-28,SAVED_W,H-(SAVED_Y-28)-40)
    pygame.draw.rect(screen,(255,255,255),r); scribble_rect(screen,r,INK,2,1)
    screen.blit(font.render("Program",True,INK),(SAVED_X+10,SAVED_Y-46))
    y=SAVED_Y; mini=16
    for i,row in enumerate(saved_rows):
        for c,v in enumerate(row["cells"][: int((SAVED_W-20)/(mini+2))]):
            cell=(SAVED_X+8+c*(mini+2),y,mini,mini)
            pygame.draw.rect(screen,PALETTE[v],cell); pygame.draw.rect(screen,GRID_LINE,cell,1)
        screen.blit(font_tiny.render(row["text"],True,INK),(SAVED_X+8,y+mini+4))
        row["_rect"]=pygame.Rect(SAVED_X+4,y,SAVED_W-12,mini+22)
        y+=mini+30
    # toast & outputs
    screen.blit(font_s.render(toast,True,(60,80,140)),(SAVED_X+10,r.bottom-28))
    oy=r.bottom-60
    for line in output_lines[-5:]:
        screen.blit(font_s.render(line,True,(40,120,40)),(SAVED_X+10,oy))
        oy+=18

# ───────── main loop ─────────
def main():
    global cursor,duck_heading,toast
    running=True
    while running:
        dt=clock.tick(FPS)/1000
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_q: running=False
                elif e.key in (pygame.K_LEFT,pygame.K_a): cursor=max(0,cursor-1); duck_heading=-1
                elif e.key in (pygame.K_RIGHT,pygame.K_d): cursor=min(ROW_LEN-1,cursor+1); duck_heading=1
                elif e.key==pygame.K_SPACE: cycle_here()
                elif e.key==pygame.K_BACKSPACE: set_here(-1)
                elif e.key==pygame.K_c: clear_row()
                elif e.key in (pygame.K_RETURN,pygame.K_KP_ENTER): add_current_row()
                elif e.key==pygame.K_r: run_program()
                elif e.key==pygame.K_s: save_duck()
                elif e.key==pygame.K_o: load_latest_duck()
                elif e.unicode and e.unicode.isdigit(): set_here(int(e.unicode))
            elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                mx,my=e.pos
                if GRID_Y<=my<GRID_Y+CELL:
                    idx=(mx-GRID_X)//CELL
                    if 0<=idx<ROW_LEN: cursor=idx
                for i,row in enumerate(saved_rows):
                    if row.get("_rect") and row["_rect"].collidepoint(mx,my):
                        load_saved_row_at(i); toast=f"loaded line {i+1}"; break

        draw_paper_bg(); 
        draw_row(); draw_duck_at_cursor(dt); draw_program_panel(); draw_header()
        pygame.display.flip()
    pygame.quit()

if __name__=="__main__": main()
