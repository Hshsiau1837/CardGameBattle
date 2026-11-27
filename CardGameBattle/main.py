import pygame
import asyncio
import sys
import os
import json
import urllib.request
import urllib.error
from loader import CardLoader
from ai_replay import ReplayRecorder
from engine import GameEngine

# Kiểm tra môi trường (Desktop hay WebAssembly/Pygbag)
try:
    import js
    IS_WEB = True
except ImportError:
    js = None
    IS_WEB = False

# Khởi tạo Pygame
pygame.init()
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AlgoCards: EDOPro Deck Builder & Battle")

# --- BẢNG MÀU & FONT CHUẨN ---
COLOR_BG = (15, 15, 20)            
COLOR_PANEL = (55, 12, 12)        
COLOR_PANEL_HOVER = (85, 18, 18)  
COLOR_BORDER = (200, 150, 50)     
COLOR_TEXT = (245, 245, 245)      
COLOR_ACCENT = (255, 215, 0)      

COLOR_MONSTER = (200, 110, 40)    
COLOR_SPELL = (30, 130, 70)       
COLOR_TRAP = (160, 40, 130)       

FONT = pygame.font.SysFont("Arial", 14)
FONT_BOLD = pygame.font.SysFont("Arial", 16, bold=True)
FONT_TITLE = pygame.font.SysFont("Arial", 20, bold=True)

class GameState:
    LOGIN = "LOGIN"
    MENU = "MENU"
    DECK_BUILDER = "DECK_BUILDER"
    BATTLE = "BATTLE"

current_state = GameState.LOGIN

ALL_CARDS = []
user_main_deck = []
user_extra_deck = []
user_side_deck = []
unlocked_cards = []
selected_card = None
recorder = ReplayRecorder()
image_cache = {}

API_BASE_URL = "http://127.0.0.1:8001"
logged_username = ""
login_user_input = ""
login_pass_input = ""
active_input_field = "username"
login_status_msg = ""

search_query = ""
search_active = False
dragging_card = None
scroll_offset = 0

game_engine = None
battle_log = []

def get_card_image(card):
    if not card or not card.get('id'):
        return None
    card_id = str(card['id'])
    if card_id in image_cache:
        return image_cache[card_id]
    img_path = os.path.join("card_images", f"{card_id}.jpg")
    if os.path.exists(img_path):
        try:
            img = pygame.image.load(img_path)
            image_cache[card_id] = img
            return img
        except Exception:
            pass
    return None

def draw_honeycomb_bg():
    SCREEN.fill(COLOR_BG)
    for x in range(0, WIDTH, 60):
        pygame.draw.line(SCREEN, (22, 22, 30), (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 60):
        pygame.draw.line(SCREEN, (22, 22, 30), (0, y), (WIDTH, y), 1)

# --- XỬ LÝ API TƯƠNG THÍCH CẢ LOCAL & WEB ---
async def api_auth(endpoint, username, password):
    global logged_username, user_main_deck, unlocked_cards, login_status_msg, current_state
    try:
        data = await post_json(f"{API_BASE_URL}{endpoint}", {
            "username": username,
            "password": password
        })
        login_status_msg = data.get("message", "")
        if data.get("status") == "success" and endpoint == "/api/login":
            logged_username = username
            unlocked_cards = data.get("unlocked_cards", [])
            saved_deck_ids = data.get("deck_data", [])
            user_main_deck = [c for c in ALL_CARDS if c["id"] in saved_deck_ids]
            current_state = GameState.MENU
    except Exception as e:
        print("API AUTH ERROR:", e)
        login_status_msg = f"{type(e).__name__}: {str(e)[:50]}"

async def api_sync_progress():
    global logged_username, user_main_deck, unlocked_cards, login_status_msg
    if not logged_username:
        return
    try:
        deck_ids = [c["id"] for c in user_main_deck]
        data = await post_json(f"{API_BASE_URL}/api/sync", {
            "username": logged_username,
            "deck_data": str(deck_ids),
            "unlocked_cards": str(unlocked_cards)
        })
        login_status_msg = data.get("message", "Da luu deck thanh cong!")
    except Exception as e:
        print("API SYNC ERROR:", e)
        login_status_msg = "Loi dong bo!"
_req_counter = 0

async def post_json(url, payload):
    global _req_counter
    _req_counter += 1
    req_id = f"req_{_req_counter}"
    payload_str = json.dumps(payload)

    if IS_WEB:
        js.window.eval(f"""
            window.{req_id} = {{ done: false, err: null, text: "" }};
            fetch({json.dumps(url)}, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: {json.dumps(payload_str)}
            }})
            .then(r => r.text())
            .then(t => {{ window.{req_id}.text = t; window.{req_id}.done = true; }})
            .catch(e => {{ window.{req_id}.err = String(e); window.{req_id}.done = true; }});
        """)
        while True:
            done_val = js.window.eval(f"window.{req_id}.done")
            if bool(done_val):
                break
            await asyncio.sleep(0.05)

        err_val = js.window.eval(f"window.{req_id}.err")
        res_text = str(js.window.eval(f"window.{req_id}.text"))
        js.window.eval(f"delete window.{req_id};")

        err_str = "" if err_val is None else str(err_val)
        if err_str and err_str.lower() != "null":
            raise RuntimeError(err_str)
        return json.loads(res_text)
    else:
        req = urllib.request.Request(
            url,
            data=payload_str.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
# --- MÀN HÌNH ĐĂNG NHẬP ---
btn_login_rect = None
btn_register_rect = None

def render_login_screen():
    draw_honeycomb_bg()
    global btn_login_rect, btn_register_rect
    center_x, center_y = WIDTH // 2, HEIGHT // 2
    
    panel = pygame.Rect(center_x - 190, center_y - 200, 380, 400)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    pygame.draw.rect(SCREEN, COLOR_BORDER, panel, 2, border_radius=8)
    
    title = FONT_TITLE.render("DANG NHAP & DANG KY", True, COLOR_ACCENT)
    SCREEN.blit(title, (center_x - title.get_width() // 2, center_y - 175))
    
    SCREEN.blit(FONT_BOLD.render("Tai khoan:", True, COLOR_TEXT), (center_x - 150, center_y - 120))
    u_box = pygame.Rect(center_x - 150, center_y - 95, 300, 35)
    u_col = COLOR_ACCENT if active_input_field == "username" else COLOR_BORDER
    pygame.draw.rect(SCREEN, (30, 30, 40), u_box, border_radius=4)
    pygame.draw.rect(SCREEN, u_col, u_box, 1, border_radius=4)
    SCREEN.blit(FONT.render(login_user_input, True, COLOR_TEXT), (u_box.x + 10, u_box.y + 8))
    
    SCREEN.blit(FONT_BOLD.render("Mat khau:", True, COLOR_TEXT), (center_x - 150, center_y - 50))
    p_box = pygame.Rect(center_x - 150, center_y - 25, 300, 35)
    p_col = COLOR_ACCENT if active_input_field == "password" else COLOR_BORDER
    pygame.draw.rect(SCREEN, (30, 30, 40), p_box, border_radius=4)
    pygame.draw.rect(SCREEN, p_col, p_box, 1, border_radius=4)
    SCREEN.blit(FONT.render("*" * len(login_pass_input), True, COLOR_TEXT), (p_box.x + 10, p_box.y + 8))
    
    btn_login_rect = pygame.Rect(center_x - 150, center_y + 30, 300, 38)
    is_l_hover = btn_login_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_l_hover else (30, 100, 50), btn_login_rect, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_login_rect, 1, border_radius=6)
    txt_l = FONT_BOLD.render("DANG NHAP", True, COLOR_TEXT)
    SCREEN.blit(txt_l, (btn_login_rect.x + btn_login_rect.width // 2 - txt_l.get_width() // 2, btn_login_rect.y + 10))

    btn_register_rect = pygame.Rect(center_x - 150, center_y + 80, 300, 38)
    is_r_hover = btn_register_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_r_hover else (50, 70, 130), btn_register_rect, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_register_rect, 1, border_radius=6)
    txt_r = FONT_BOLD.render("DANG KY TAI KHOAN", True, COLOR_TEXT)
    SCREEN.blit(txt_r, (btn_register_rect.x + btn_register_rect.width // 2 - txt_r.get_width() // 2, btn_register_rect.y + 10))
    
    if login_status_msg:
        msg_surf = FONT.render(login_status_msg, True, COLOR_ACCENT)
        SCREEN.blit(msg_surf, (center_x - msg_surf.get_width() // 2, center_y + 135))

# --- MENU CHÍNH ---
def render_menu():
    draw_honeycomb_bg()
    center_x, center_y = WIDTH // 2, HEIGHT // 2 - 20
    
    points = [(center_x, center_y - 120), (center_x - 140, center_y + 80), (center_x + 140, center_y + 80)]
    pygame.draw.polygon(SCREEN, (35, 10, 10), points)
    pygame.draw.polygon(SCREEN, COLOR_BORDER, points, 3)

    title = FONT_TITLE.render("ALGO CARDS: DECK SYSTEM", True, COLOR_ACCENT)
    SCREEN.blit(title, (center_x - title.get_width() // 2, center_y - 85))

    user_info = FONT.render(f"Xin chao: {logged_username}", True, (180, 255, 180))
    SCREEN.blit(user_info, (center_x - user_info.get_width() // 2, center_y - 50))

    menu_items = [
        ("Xay dung Bo bai (Deck Builder)", GameState.DECK_BUILDER),
        ("Dau truong Online (VS AI)", GameState.BATTLE),
        ("Dang xuat", GameState.LOGIN)
    ]

    start_y = center_y - 20
    for idx, (text, action) in enumerate(menu_items):
        rect = pygame.Rect(center_x - 140, start_y + idx * 50, 280, 40)
        is_hover = rect.collidepoint(pygame.mouse.get_pos())
        color = COLOR_PANEL_HOVER if is_hover else COLOR_PANEL
        pygame.draw.rect(SCREEN, color, rect, border_radius=6)
        pygame.draw.rect(SCREEN, COLOR_BORDER, rect, 1, border_radius=6)
        txt_surf = FONT_BOLD.render(text, True, COLOR_TEXT)
        SCREEN.blit(txt_surf, (rect.x + rect.width // 2 - txt_surf.get_width() // 2, rect.y + 10))

def render_card_thumbnail(x, y, width, height, card, is_selected=False):
    rect = pygame.Rect(x, y, width, height)
    card_img = get_card_image(card)
    if card_img:
        scaled_img = pygame.transform.scale(card_img, (width, height))
        SCREEN.blit(scaled_img, (x, y))
    else:
        ctype = card.get('type', 'Monster')
        frame_color = COLOR_MONSTER if 'Monster' in ctype else (COLOR_TRAP if 'Trap' in ctype else COLOR_SPELL)
        pygame.draw.rect(SCREEN, (40, 40, 50), rect, border_radius=3)
        pygame.draw.rect(SCREEN, frame_color, rect, 1, border_radius=3)
        name_surf = FONT.render(card['name'][:8], True, COLOR_TEXT)
        SCREEN.blit(name_surf, (x + 2, y + 2))

    border_col = COLOR_ACCENT if is_selected else (100, 100, 100)
    pygame.draw.rect(SCREEN, border_col, rect, 1, border_radius=3)

right_list_rects = []
main_deck_rects = []
extra_deck_rects = []
side_deck_rects = []
btn_save_deck_rect = None

# --- DECK BUILDER ---
def render_deck_builder():
    draw_honeycomb_bg()
    global right_list_rects, main_deck_rects, extra_deck_rects, side_deck_rects, btn_save_deck_rect
    right_list_rects = []
    main_deck_rects = []
    extra_deck_rects = []
    side_deck_rects = []

    left_panel = pygame.Rect(15, 15, 290, HEIGHT - 30)
    pygame.draw.rect(SCREEN, COLOR_PANEL, left_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, left_panel, 1, border_radius=6)

    if selected_card:
        card_art = pygame.Rect(35, 30, 250, 310)
        card_img = get_card_image(selected_card)
        if card_img:
            scaled_img = pygame.transform.scale(card_img, (250, 310))
            SCREEN.blit(scaled_img, (35, 30))
        else:
            pygame.draw.rect(SCREEN, (30, 30, 40), card_art, border_radius=4)
        pygame.draw.rect(SCREEN, COLOR_ACCENT, card_art, 2, border_radius=4)
        
        c_name = FONT_BOLD.render(selected_card['name'][:24], True, COLOR_TEXT)
        c_type = FONT.render(f"[{selected_card.get('type', 'Monster')}]", True, (255, 215, 0))
        c_stats = FONT.render(f"ATK/ {selected_card.get('ATK', 0)}   DEF/ {selected_card.get('DEF', 0)}", True, COLOR_TEXT)
        
        SCREEN.blit(c_name, (35, 350))
        SCREEN.blit(c_type, (35, 375))
        SCREEN.blit(c_stats, (35, 398))

        desc_box = pygame.Rect(35, 425, 250, 260)
        pygame.draw.rect(SCREEN, (30, 10, 10), desc_box, border_radius=4)
        pygame.draw.rect(SCREEN, COLOR_BORDER, desc_box, 1, border_radius=4)
        
        desc_text = selected_card.get('effect', 'Khong co mo ta.')
        words = desc_text.split(' ')
        line, line_y = "", 435
        for word in words:
            test_line = line + word + " "
            if FONT.size(test_line)[0] < 235:
                line = test_line
            else:
                SCREEN.blit(FONT.render(line, True, (220, 220, 220)), (42, line_y))
                line = word + " "
                line_y += 18
                if line_y > 670: break
        SCREEN.blit(FONT.render(line, True, (220, 220, 220)), (42, line_y))

    center_panel = pygame.Rect(320, 15, 620, HEIGHT - 30)
    pygame.draw.rect(SCREEN, (25, 25, 35), center_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, center_panel, 1, border_radius=6)

    top_tools = pygame.Rect(335, 25, 590, 35)
    pygame.draw.rect(SCREEN, COLOR_PANEL, top_tools, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BORDER, top_tools, 1, border_radius=4)
    SCREEN.blit(FONT_BOLD.render(f"Main: {len(user_main_deck)}/40 | [ESC] Menu", True, COLOR_TEXT), (345, 32))

    btn_save_deck_rect = pygame.Rect(790, 28, 120, 28)
    is_save_hover = btn_save_deck_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(SCREEN, (40, 120, 60) if is_save_hover else (20, 80, 40), btn_save_deck_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_ACCENT, btn_save_deck_rect, 1, border_radius=4)
    SCREEN.blit(FONT_BOLD.render("LUU DECK", True, COLOR_TEXT), (825, 33))

    main_deck_box = pygame.Rect(335, 68, 590, 315)
    pygame.draw.rect(SCREEN, (18, 18, 25), main_deck_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, main_deck_box, 1, border_radius=6)
    SCREEN.blit(FONT_BOLD.render("Main Deck (40 slots):", True, COLOR_ACCENT), (345, 74))

    for idx in range(40):
        col = idx % 10
        row = idx // 10
        c_x = 343 + col * 57
        c_y = 96 + row * 72
        slot_rect = pygame.Rect(c_x, c_y, 48, 68)
        pygame.draw.rect(SCREEN, (30, 32, 42), slot_rect, border_radius=3)
        pygame.draw.rect(SCREEN, (50, 55, 70), slot_rect, 1, border_radius=3)
        if idx < len(user_main_deck):
            card = user_main_deck[idx]
            main_deck_rects.append((slot_rect, idx))
            render_card_thumbnail(c_x, c_y, 48, 68, card)

    extra_box = pygame.Rect(335, 390, 590, 140)
    pygame.draw.rect(SCREEN, COLOR_PANEL, extra_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, extra_box, 1, border_radius=6)
    SCREEN.blit(FONT_BOLD.render("Extra Deck (15 slots):", True, COLOR_TEXT), (345, 396))
    for idx in range(15):
        col = idx % 8
        row = idx // 8
        c_x = 343 + col * 57
        c_y = 416 + row * 56
        slot_rect = pygame.Rect(c_x, c_y, 48, 52)
        pygame.draw.rect(SCREEN, (40, 20, 20), slot_rect, border_radius=3)
        if idx < len(user_extra_deck):
            card = user_extra_deck[idx]
            extra_deck_rects.append((slot_rect, idx))
            render_card_thumbnail(c_x, c_y, 48, 52, card)

    side_box = pygame.Rect(335, 538, 590, 140)
    pygame.draw.rect(SCREEN, COLOR_PANEL, side_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, side_box, 1, border_radius=6)
    SCREEN.blit(FONT_BOLD.render("Side Deck (15 slots):", True, COLOR_TEXT), (345, 544))
    for idx in range(15):
        col = idx % 8
        row = idx // 8
        c_x = 343 + col * 57
        c_y = 564 + row * 56
        slot_rect = pygame.Rect(c_x, c_y, 48, 52)
        pygame.draw.rect(SCREEN, (40, 20, 20), slot_rect, border_radius=3)
        if idx < len(user_side_deck):
            card = user_side_deck[idx]
            side_deck_rects.append((slot_rect, idx))
            render_card_thumbnail(c_x, c_y, 48, 52, card)

    right_panel = pygame.Rect(955, 15, 310, HEIGHT - 30)
    pygame.draw.rect(SCREEN, COLOR_PANEL, right_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, right_panel, 1, border_radius=6)

    search_box_rect = pygame.Rect(970, 30, 280, 32)
    bg_search = (70, 20, 20) if search_active else (40, 40, 50)
    pygame.draw.rect(SCREEN, bg_search, search_box_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_ACCENT if search_active else COLOR_BORDER, search_box_rect, 1, border_radius=4)
    display_text = search_query if search_query else "Nhap ten card de tim..."
    txt_col = COLOR_TEXT if search_query else (150, 150, 150)
    SCREEN.blit(FONT.render(display_text, True, txt_col), (search_box_rect.x + 10, search_box_rect.y + 7))

    if search_query.strip() != "":
        filtered_cards = [c for c in ALL_CARDS if search_query.lower() in c['name'].lower()]
        results_header = pygame.Rect(970, 70, 280, 30)
        pygame.draw.rect(SCREEN, (30, 10, 10), results_header, border_radius=4)
        SCREEN.blit(FONT.render(f"Ket qua ({len(filtered_cards)}) - Keo tha vao Deck", True, COLOR_ACCENT), (980, 76))

        ry = 110 - scroll_offset
        for idx, card in enumerate(filtered_cards): 
            if -60 < ry < HEIGHT:
                item_rect = pygame.Rect(970, ry, 280, 52)
                is_sel = (selected_card and selected_card['id'] == card['id'])
                right_list_rects.append((item_rect, card))
                render_card_thumbnail(970, ry, 38, 52, card, is_selected=is_sel)
                name_surf = FONT_BOLD.render(card['name'][:24], True, COLOR_TEXT)
                info_surf = FONT.render(f"ATK: {card.get('ATK', 0)} / DEF: {card.get('DEF', 0)}", True, (200, 200, 200))
                SCREEN.blit(name_surf, (1018, ry + 6))
                SCREEN.blit(info_surf, (1018, ry + 28))
            ry += 56

    if dragging_card:
        m_pos = pygame.mouse.get_pos()
        render_card_thumbnail(m_pos[0] - 20, m_pos[1] - 30, 40, 56, dragging_card, is_selected=True)

btn_next_phase_rect = None

# --- BÀN ĐẤU (BATTLE) ---
def render_battle_field():
    draw_honeycomb_bg()
    global game_engine, battle_log, btn_next_phase_rect

    if not game_engine:
        sample_p1 = user_main_deck if len(user_main_deck) >= 5 else [
            {"id": "STK-01", "name": "Stack Push", "category": "Stack", "cost": 1},
            {"id": "GRA-01", "name": "BFS Traversal", "category": "Graph", "cost": 2},
        ]
        sample_p2 = [
            {"id": "DP-01", "name": "Memoization Cache", "category": "DP", "cost": 1},
        ]
        game_engine = GameEngine(logged_username or "Player1", sample_p1, "AI Opponent", sample_p2)
        battle_log = [f"Bat dau tran dau! Luot cua {game_engine.current_turn_player.username}"]

    pygame.draw.rect(SCREEN, (160, 20, 20), pygame.Rect(330, 15, 260, 35), border_radius=4)
    pygame.draw.rect(SCREEN, (20, 120, 40), pygame.Rect(690, 15, 260, 35), border_radius=4)
    
    p2_info = FONT_BOLD.render(f"{game_engine.player2.username} | LP: {game_engine.player2.hp}", True, COLOR_TEXT)
    p1_info = FONT_BOLD.render(f"{game_engine.player1.username} | LP: {game_engine.player1.hp}", True, COLOR_TEXT)
    SCREEN.blit(p2_info, (340, 23))
    SCREEN.blit(p1_info, (700, 23))

    mat_rect = pygame.Rect(330, 60, 620, 440)
    pygame.draw.rect(SCREEN, (18, 18, 26), mat_rect, border_radius=8)
    pygame.draw.rect(SCREEN, COLOR_BORDER, mat_rect, 2, border_radius=8)

    phase_txt = FONT_TITLE.render(f"LUOT {game_engine.turn_count}: {game_engine.current_phase}", True, COLOR_ACCENT)
    SCREEN.blit(phase_txt, (WIDTH // 2 - phase_txt.get_width() // 2, 75))

    btn_next_phase_rect = pygame.Rect(WIDTH // 2 - 80, 115, 160, 32)
    is_ph_hover = btn_next_phase_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_ph_hover else COLOR_PANEL, btn_next_phase_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_next_phase_rect, 1, border_radius=4)
    SCREEN.blit(FONT_BOLD.render("CHUYEN PHASE", True, COLOR_TEXT), (WIDTH // 2 - 50, 122))

    SCREEN.blit(FONT_BOLD.render(f"Tay bai Player (Mana: {game_engine.player1.mana}/{game_engine.player1.max_mana}):", True, COLOR_TEXT), (345, 370))
    for idx, card in enumerate(game_engine.player1.hand):
        hx = 345 + idx * 75
        hy = 395
        render_card_thumbnail(hx, hy, 65, 90, card)

    log_box = pygame.Rect(960, 60, 305, 440)
    pygame.draw.rect(SCREEN, COLOR_PANEL, log_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, log_box, 1, border_radius=6)
    SCREEN.blit(FONT_BOLD.render("Nhat ky tran dau (Replay):", True, COLOR_ACCENT), (970, 70))
    
    ly = 100
    for entry in battle_log[-18:]:
        SCREEN.blit(FONT.render(entry[:45], True, COLOR_TEXT), (970, ly))
        ly += 20

    SCREEN.blit(FONT.render("Nhan [ESC] de quay ve Menu", True, (180, 180, 180)), (WIDTH // 2 - 80, HEIGHT - 30))

# --- VÒNG LẶP ASYNC CHÍNH ---
async def main():
    global current_state, ALL_CARDS, selected_card, user_main_deck, user_extra_deck, user_side_deck
    global search_query, search_active, dragging_card, scroll_offset
    global login_user_input, login_pass_input, active_input_field, game_engine, battle_log

    card_loader = CardLoader()
    try:
        ALL_CARDS = card_loader.load_and_validate()
    except Exception as e:
        ALL_CARDS = []
        
    if ALL_CARDS and not selected_card:
        selected_card = ALL_CARDS[0]

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if mouse_pos[0] > 955: 
                    scroll_offset -= event.y * 30
                    scroll_offset = max(0, scroll_offset)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                center_x, center_y = WIDTH // 2, HEIGHT // 2

                if current_state == GameState.LOGIN:
                    u_box = pygame.Rect(center_x - 150, center_y - 95, 300, 35)
                    p_box = pygame.Rect(center_x - 150, center_y - 25, 300, 35)

                    if u_box.collidepoint(mouse_pos):
                        active_input_field = "username"
                    elif p_box.collidepoint(mouse_pos):
                        active_input_field = "password"
                    elif btn_login_rect and btn_login_rect.collidepoint(mouse_pos):
                        if login_user_input and login_pass_input:
                            await api_auth("/api/login", login_user_input, login_pass_input)
                    elif btn_register_rect and btn_register_rect.collidepoint(mouse_pos):
                        if login_user_input and login_pass_input:
                            await api_auth("/api/register", login_user_input, login_pass_input)

                elif current_state == GameState.MENU:
                    if pygame.Rect(center_x - 140, center_y - 20, 280, 40).collidepoint(mouse_pos):
                        current_state = GameState.DECK_BUILDER
                    elif pygame.Rect(center_x - 140, center_y + 30, 280, 40).collidepoint(mouse_pos):
                        game_engine = None
                        current_state = GameState.BATTLE
                    elif pygame.Rect(center_x - 140, center_y + 80, 280, 40).collidepoint(mouse_pos):
                        current_state = GameState.LOGIN

                elif current_state == GameState.DECK_BUILDER:
                    search_box_rect = pygame.Rect(970, 30, 280, 32)
                    search_active = search_box_rect.collidepoint(mouse_pos)

                    if btn_save_deck_rect and btn_save_deck_rect.collidepoint(mouse_pos):
                        await api_sync_progress()

                    for rect, card in right_list_rects:
                        if rect.collidepoint(mouse_pos):
                            selected_card = card
                            dragging_card = card

                    for rect, idx in main_deck_rects:
                        if rect.collidepoint(mouse_pos) and idx < len(user_main_deck):
                            user_main_deck.pop(idx)

                elif current_state == GameState.BATTLE:
                    if btn_next_phase_rect and btn_next_phase_rect.collidepoint(mouse_pos) and game_engine:
                        msg = game_engine.next_phase()
                        battle_log.append(msg)
                        recorder.log(game_engine.turn_count, game_engine.current_phase, game_engine.current_turn_player.username, "NEXT_PHASE", msg)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging_card and current_state == GameState.DECK_BUILDER:
                    mouse_pos = pygame.mouse.get_pos()
                    main_deck_box = pygame.Rect(335, 68, 590, 315)
                    if main_deck_box.collidepoint(mouse_pos) and len(user_main_deck) < 40:
                        user_main_deck.append(dragging_card)
                    dragging_card = None

            if event.type == pygame.KEYDOWN:
                if current_state == GameState.LOGIN:
                    if event.key == pygame.K_TAB:
                        active_input_field = "password" if active_input_field == "username" else "username"
                    elif event.key == pygame.K_RETURN:
                        if login_user_input and login_pass_input:
                            await api_auth("/api/login", login_user_input, login_pass_input)
                    elif event.key == pygame.K_BACKSPACE:
                        if active_input_field == "username":
                            login_user_input = login_user_input[:-1]
                        else:
                            login_pass_input = login_pass_input[:-1]
                    elif event.unicode.isprintable():
                        if active_input_field == "username":
                            login_user_input += event.unicode
                        else:
                            login_pass_input += event.unicode

                elif current_state == GameState.DECK_BUILDER and search_active:
                    if event.key == pygame.K_BACKSPACE:
                        search_query = search_query[:-1]
                    elif event.key == pygame.K_RETURN:
                        search_active = False
                    elif event.unicode.isprintable():
                        search_query += event.unicode
                        scroll_offset = 0

                if event.key == pygame.K_ESCAPE and current_state != GameState.LOGIN:
                    current_state = GameState.MENU

        if current_state == GameState.LOGIN:
            render_login_screen()
        elif current_state == GameState.MENU:
            render_menu()
        elif current_state == GameState.DECK_BUILDER:
            render_deck_builder()
        elif current_state == GameState.BATTLE:
            render_battle_field()

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())