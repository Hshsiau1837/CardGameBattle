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

try:
    import js
    IS_WEB = True
except ImportError:
    js = None
    IS_WEB = False

pygame.init()
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AlgoCards: EDOPro Deck Builder & Battle")

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
card_by_id = {}
filtered_cache_key = None
filtered_cache_list = []

user_main_deck = []
user_extra_deck = []
user_side_deck = []
unlocked_cards = []
selected_card = None
recorder = ReplayRecorder()
image_cache = {}
scaled_image_cache = {}
text_cache = {}
bg_surface = None

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
_req_counter = 0

btn_login_rect = None
btn_register_rect = None
right_list_rects = []
main_deck_rects = []
extra_deck_rects = []
side_deck_rects = []
btn_save_deck_rect = None
btn_next_phase_rect = None


def get_card_image(card):
    if not card or not card.get("id"):
        return None
    card_id = str(card["id"])
    if card_id in image_cache:
        return image_cache[card_id]
    img_path = os.path.join("card_images", f"{card_id}.jpg")
    if os.path.exists(img_path):
        try:
            img = pygame.image.load(img_path).convert()
            image_cache[card_id] = img
            return img
        except Exception:
            try:
                img = pygame.image.load(img_path)
                image_cache[card_id] = img
                return img
            except Exception:
                pass
    image_cache[card_id] = None
    return None


def get_scaled_card_image(card, width, height):
    if not card or not card.get("id"):
        return None
    card_id = str(card["id"])
    w, h = int(width), int(height)
    key = (card_id, w, h)
    if key in scaled_image_cache:
        return scaled_image_cache[key]
    base_img = get_card_image(card)
    if base_img is None:
        return None
    scaled = pygame.transform.smoothscale(base_img, (w, h))
    if len(scaled_image_cache) > 512:
        scaled_image_cache.clear()
    scaled_image_cache[key] = scaled
    return scaled


def get_cached_text(text, font, color):
    s = str(text)
    key = (s, id(font), color)
    surf = text_cache.get(key)
    if surf is None:
        surf = font.render(s, True, color)
        if len(text_cache) > 1024:
            text_cache.clear()
        text_cache[key] = surf
    return surf


def draw_text(text, font, color, pos, center=False):
    surf = get_cached_text(text, font, color)
    rect = surf.get_rect(center=pos) if center else surf.get_rect(topleft=pos)
    SCREEN.blit(surf, rect)
    return rect


def get_bg_surface():
    global bg_surface
    if bg_surface is None:
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(COLOR_BG)
        for x in range(0, WIDTH, 60):
            pygame.draw.line(surf, (22, 22, 30), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 60):
            pygame.draw.line(surf, (22, 22, 30), (0, y), (WIDTH, y), 1)
        bg_surface = surf
    return bg_surface


def draw_honeycomb_bg():
    SCREEN.blit(get_bg_surface(), (0, 0))


def get_filtered_cards(query):
    global filtered_cache_key, filtered_cache_list
    q = query.strip().lower()
    if q == filtered_cache_key:
        return filtered_cache_list
    if not q:
        filtered_cache_key = ""
        filtered_cache_list = []
        return filtered_cache_list
    filtered_cache_key = q
    filtered_cache_list = [c for c in ALL_CARDS if q in str(c.get("name", "")).lower()]
    return filtered_cache_list


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
            user_main_deck = [card_by_id[cid] for cid in saved_deck_ids if cid in card_by_id]
            current_state = GameState.MENU
    except Exception as e:
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
        login_status_msg = "Loi dong bo!"


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
            await asyncio.sleep(0.01)

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


def render_login_screen():
    draw_honeycomb_bg()
    global btn_login_rect, btn_register_rect
    center_x, center_y = WIDTH // 2, HEIGHT // 2
    mouse_pos = pygame.mouse.get_pos()

    panel = pygame.Rect(center_x - 190, center_y - 200, 380, 400)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    pygame.draw.rect(SCREEN, COLOR_BORDER, panel, 2, border_radius=8)

    draw_text("DANG NHAP & DANG KY", FONT_TITLE, COLOR_ACCENT, (center_x, center_y - 165), center=True)

    draw_text("Tai khoan:", FONT_BOLD, COLOR_TEXT, (center_x - 150, center_y - 120))
    u_box = pygame.Rect(center_x - 150, center_y - 95, 300, 35)
    u_col = COLOR_ACCENT if active_input_field == "username" else COLOR_BORDER
    pygame.draw.rect(SCREEN, (30, 30, 40), u_box, border_radius=4)
    pygame.draw.rect(SCREEN, u_col, u_box, 1, border_radius=4)
    draw_text(login_user_input, FONT, COLOR_TEXT, (u_box.x + 10, u_box.y + 8))

    draw_text("Mat khau:", FONT_BOLD, COLOR_TEXT, (center_x - 150, center_y - 50))
    p_box = pygame.Rect(center_x - 150, center_y - 25, 300, 35)
    p_col = COLOR_ACCENT if active_input_field == "password" else COLOR_BORDER
    pygame.draw.rect(SCREEN, (30, 30, 40), p_box, border_radius=4)
    pygame.draw.rect(SCREEN, p_col, p_box, 1, border_radius=4)
    draw_text("*" * len(login_pass_input), FONT, COLOR_TEXT, (p_box.x + 10, p_box.y + 8))

    btn_login_rect = pygame.Rect(center_x - 150, center_y + 30, 300, 38)
    is_l_hover = btn_login_rect.collidepoint(mouse_pos)
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_l_hover else (30, 100, 50), btn_login_rect, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_login_rect, 1, border_radius=6)
    draw_text("DANG NHAP", FONT_BOLD, COLOR_TEXT, btn_login_rect.center, center=True)

    btn_register_rect = pygame.Rect(center_x - 150, center_y + 80, 300, 38)
    is_r_hover = btn_register_rect.collidepoint(mouse_pos)
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_r_hover else (50, 70, 130), btn_register_rect, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_register_rect, 1, border_radius=6)
    draw_text("DANG KY TAI KHOAN", FONT_BOLD, COLOR_TEXT, btn_register_rect.center, center=True)

    if login_status_msg:
        draw_text(login_status_msg, FONT, COLOR_ACCENT, (center_x, center_y + 143), center=True)


def render_menu():
    draw_honeycomb_bg()
    center_x, center_y = WIDTH // 2, HEIGHT // 2 - 20
    mouse_pos = pygame.mouse.get_pos()

    points = [(center_x, center_y - 120), (center_x - 140, center_y + 80), (center_x + 140, center_y + 80)]
    pygame.draw.polygon(SCREEN, (35, 10, 10), points)
    pygame.draw.polygon(SCREEN, COLOR_BORDER, points, 3)

    draw_text("ALGO CARDS: DECK SYSTEM", FONT_TITLE, COLOR_ACCENT, (center_x, center_y - 75), center=True)
    draw_text(f"Xin chao: {logged_username}", FONT, (180, 255, 180), (center_x, center_y - 42), center=True)

    menu_items = [
        ("Xay dung Bo bai (Deck Builder)", GameState.DECK_BUILDER),
        ("Dau truong Online (VS AI)", GameState.BATTLE),
        ("Dang xuat", GameState.LOGIN)
    ]

    start_y = center_y - 20
    for idx, (text, _) in enumerate(menu_items):
        rect = pygame.Rect(center_x - 140, start_y + idx * 50, 280, 40)
        is_hover = rect.collidepoint(mouse_pos)
        color = COLOR_PANEL_HOVER if is_hover else COLOR_PANEL
        pygame.draw.rect(SCREEN, color, rect, border_radius=6)
        pygame.draw.rect(SCREEN, COLOR_BORDER, rect, 1, border_radius=6)
        draw_text(text, FONT_BOLD, COLOR_TEXT, rect.center, center=True)


def render_card_thumbnail(x, y, width, height, card, is_selected=False):
    rect = pygame.Rect(x, y, width, height)
    scaled_img = get_scaled_card_image(card, width, height)
    if scaled_img:
        SCREEN.blit(scaled_img, (x, y))
    else:
        ctype = card.get("type", "Monster")
        frame_color = COLOR_MONSTER if "Monster" in ctype else (COLOR_TRAP if "Trap" in ctype else COLOR_SPELL)
        pygame.draw.rect(SCREEN, (40, 40, 50), rect, border_radius=3)
        pygame.draw.rect(SCREEN, frame_color, rect, 1, border_radius=3)
        draw_text(str(card.get("name", ""))[:8], FONT, COLOR_TEXT, (x + 2, y + 2))

    border_col = COLOR_ACCENT if is_selected else (100, 100, 100)
    pygame.draw.rect(SCREEN, border_col, rect, 1, border_radius=3)


def render_deck_builder():
    draw_honeycomb_bg()
    global right_list_rects, main_deck_rects, extra_deck_rects, side_deck_rects, btn_save_deck_rect
    right_list_rects = []
    main_deck_rects = []
    extra_deck_rects = []
    side_deck_rects = []
    mouse_pos = pygame.mouse.get_pos()

    left_panel = pygame.Rect(15, 15, 290, HEIGHT - 30)
    pygame.draw.rect(SCREEN, COLOR_PANEL, left_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, left_panel, 1, border_radius=6)

    if selected_card:
        card_art = pygame.Rect(35, 30, 250, 310)
        scaled_img = get_scaled_card_image(selected_card, 250, 310)
        if scaled_img:
            SCREEN.blit(scaled_img, (35, 30))
        else:
            pygame.draw.rect(SCREEN, (30, 30, 40), card_art, border_radius=4)
        pygame.draw.rect(SCREEN, COLOR_ACCENT, card_art, 2, border_radius=4)

        draw_text(str(selected_card.get("name", ""))[:24], FONT_BOLD, COLOR_TEXT, (35, 350))
        draw_text(f"[{selected_card.get('type', 'Monster')}]", FONT, (255, 215, 0), (35, 375))
        draw_text(f"ATK/ {selected_card.get('ATK', 0)}   DEF/ {selected_card.get('DEF', 0)}", FONT, COLOR_TEXT, (35, 398))

        desc_box = pygame.Rect(35, 425, 250, 260)
        pygame.draw.rect(SCREEN, (30, 10, 10), desc_box, border_radius=4)
        pygame.draw.rect(SCREEN, COLOR_BORDER, desc_box, 1, border_radius=4)

        desc_text = str(selected_card.get("effect", "Khong co mo ta."))
        words = desc_text.split(" ")
        line, line_y = "", 435
        for word in words:
            test_line = line + word + " "
            if FONT.size(test_line)[0] < 235:
                line = test_line
            else:
                draw_text(line, FONT, (220, 220, 220), (42, line_y))
                line = word + " "
                line_y += 18
                if line_y > 670:
                    break
        if line_y <= 670 and line:
            draw_text(line, FONT, (220, 220, 220), (42, line_y))

    center_panel = pygame.Rect(320, 15, 620, HEIGHT - 30)
    pygame.draw.rect(SCREEN, (25, 25, 35), center_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, center_panel, 1, border_radius=6)

    top_tools = pygame.Rect(335, 25, 590, 35)
    pygame.draw.rect(SCREEN, COLOR_PANEL, top_tools, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BORDER, top_tools, 1, border_radius=4)
    draw_text(f"Main: {len(user_main_deck)}/40 | [ESC] Menu", FONT_BOLD, COLOR_TEXT, (345, 32))

    btn_save_deck_rect = pygame.Rect(790, 28, 120, 28)
    is_save_hover = btn_save_deck_rect.collidepoint(mouse_pos)
    pygame.draw.rect(SCREEN, (40, 120, 60) if is_save_hover else (20, 80, 40), btn_save_deck_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_ACCENT, btn_save_deck_rect, 1, border_radius=4)
    draw_text("LUU DECK", FONT_BOLD, COLOR_TEXT, btn_save_deck_rect.center, center=True)

    main_deck_box = pygame.Rect(335, 68, 590, 315)
    pygame.draw.rect(SCREEN, (18, 18, 25), main_deck_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, main_deck_box, 1, border_radius=6)
    draw_text("Main Deck (40 slots):", FONT_BOLD, COLOR_ACCENT, (345, 74))

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
    draw_text("Extra Deck (15 slots):", FONT_BOLD, COLOR_TEXT, (345, 396))
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
    draw_text("Side Deck (15 slots):", FONT_BOLD, COLOR_TEXT, (345, 544))
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
    draw_text(display_text, FONT, txt_col, (search_box_rect.x + 10, search_box_rect.y + 7))

    if search_query.strip() != "":
        filtered_cards = get_filtered_cards(search_query)
        results_header = pygame.Rect(970, 70, 280, 30)
        pygame.draw.rect(SCREEN, (30, 10, 10), results_header, border_radius=4)
        draw_text(f"Ket qua ({len(filtered_cards)}) - Keo tha vao Deck", FONT, COLOR_ACCENT, (980, 76))

        ry = 110 - scroll_offset
        for card in filtered_cards:
            if -60 < ry < HEIGHT:
                item_rect = pygame.Rect(970, ry, 280, 52)
                is_sel = bool(selected_card and selected_card.get("id") == card.get("id"))
                right_list_rects.append((item_rect, card))
                render_card_thumbnail(970, ry, 38, 52, card, is_selected=is_sel)
                draw_text(str(card.get("name", ""))[:24], FONT_BOLD, COLOR_TEXT, (1018, ry + 6))
                draw_text(f"ATK: {card.get('ATK', 0)} / DEF: {card.get('DEF', 0)}", FONT, (200, 200, 200), (1018, ry + 28))
            ry += 56

    if dragging_card:
        render_card_thumbnail(mouse_pos[0] - 20, mouse_pos[1] - 30, 40, 56, dragging_card, is_selected=True)


def render_battle_field():
    draw_honeycomb_bg()
    global game_engine, battle_log, btn_next_phase_rect
    mouse_pos = pygame.mouse.get_pos()

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

    draw_text(f"{game_engine.player2.username} | LP: {game_engine.player2.hp}", FONT_BOLD, COLOR_TEXT, (340, 23))
    draw_text(f"{game_engine.player1.username} | LP: {game_engine.player1.hp}", FONT_BOLD, COLOR_TEXT, (700, 23))

    mat_rect = pygame.Rect(330, 60, 620, 440)
    pygame.draw.rect(SCREEN, (18, 18, 26), mat_rect, border_radius=8)
    pygame.draw.rect(SCREEN, COLOR_BORDER, mat_rect, 2, border_radius=8)

    draw_text(f"LUOT {game_engine.turn_count}: {game_engine.current_phase}", FONT_TITLE, COLOR_ACCENT, (WIDTH // 2, 88), center=True)

    btn_next_phase_rect = pygame.Rect(WIDTH // 2 - 80, 115, 160, 32)
    is_ph_hover = btn_next_phase_rect.collidepoint(mouse_pos)
    pygame.draw.rect(SCREEN, COLOR_PANEL_HOVER if is_ph_hover else COLOR_PANEL, btn_next_phase_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BORDER, btn_next_phase_rect, 1, border_radius=4)
    draw_text("CHUYEN PHASE", FONT_BOLD, COLOR_TEXT, btn_next_phase_rect.center, center=True)

    draw_text(f"Tay bai Player (Mana: {game_engine.player1.mana}/{game_engine.player1.max_mana}):", FONT_BOLD, COLOR_TEXT, (345, 370))
    for idx, card in enumerate(game_engine.player1.hand):
        hx = 345 + idx * 75
        hy = 395
        render_card_thumbnail(hx, hy, 65, 90, card)

    log_box = pygame.Rect(960, 60, 305, 440)
    pygame.draw.rect(SCREEN, COLOR_PANEL, log_box, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, log_box, 1, border_radius=6)
    draw_text("Nhat ky tran dau (Replay):", FONT_BOLD, COLOR_ACCENT, (970, 70))

    ly = 100
    for entry in battle_log[-18:]:
        draw_text(str(entry)[:45], FONT, COLOR_TEXT, (970, ly))
        ly += 20

    draw_text("Nhan [ESC] de quay ve Menu", FONT, (180, 180, 180), (WIDTH // 2, HEIGHT - 22), center=True)


async def main():
    global current_state, ALL_CARDS, card_by_id, selected_card, user_main_deck, user_extra_deck, user_side_deck
    global search_query, search_active, dragging_card, scroll_offset
    global login_user_input, login_pass_input, active_input_field, game_engine, battle_log

    card_loader = CardLoader()
    try:
        ALL_CARDS = card_loader.load_and_validate()
    except Exception:
        ALL_CARDS = []

    card_by_id = {c["id"]: c for c in ALL_CARDS if isinstance(c, dict) and "id" in c}
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
                    menu_cy = HEIGHT // 2 - 20
                    if pygame.Rect(center_x - 140, menu_cy - 20, 280, 40).collidepoint(mouse_pos):
                        current_state = GameState.DECK_BUILDER
                    elif pygame.Rect(center_x - 140, menu_cy + 30, 280, 40).collidepoint(mouse_pos):
                        game_engine = None
                        current_state = GameState.BATTLE
                    elif pygame.Rect(center_x - 140, menu_cy + 80, 280, 40).collidepoint(mouse_pos):
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