import pygame
import asyncio
import sys
import os
import urllib.request
from loader import CardLoader
from deck_builder import DeckBuilder
from ai_replay import ReplayRecorder
from demo_task4 import Task4App

# Khởi tạo Pygame
pygame.init()
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AlgoCards: EDOPro Precise Deck Builder")

# --- BẢNG MÀU EDOPro THEME ---
COLOR_BG = (15, 15, 20)          
COLOR_PANEL = (55, 12, 12)        
COLOR_PANEL_HOVER = (85, 18, 18)  
COLOR_BORDER = (200, 150, 50)     
COLOR_TEXT = (245, 245, 245)      
COLOR_ACCENT = (255, 215, 0)      

COLOR_MONSTER = (200, 110, 40)    
COLOR_SPELL = (30, 130, 70)       
COLOR_TRAP = (160, 40, 130)       

FONT = pygame.font.SysFont("Segoe UI", 12)
FONT_BOLD = pygame.font.SysFont("Segoe UI", 14, bold=True)
FONT_TITLE = pygame.font.SysFont("Segoe UI", 22, bold=True)

class GameState:
    MENU = "MENU"
    DECK_BUILDER = "DECK_BUILDER"
    BALANCE = "BALANCE"
    BATTLE = "BATTLE"

current_state = GameState.MENU

# Load dữ liệu thẻ từ file local hoặc API
card_loader = CardLoader()
try:
    ALL_CARDS = card_loader.load_and_validate()
except Exception:
    ALL_CARDS = []

# Khởi tạo DeckBuilder quản lý luật bộ bài
deck_manager = DeckBuilder(ALL_CARDS)
user_main_deck = deck_manager.user_deck
user_extra_deck = []
user_side_deck = []

selected_card = ALL_CARDS[0] if ALL_CARDS else None
recorder = ReplayRecorder()
image_cache = {}

# Trạng thái tìm kiếm, kéo thả & cuộn, sắp xếp bảng cân bằng
search_query = ""
search_active = False
dragging_card = None
scroll_offset = 0
balance_scroll_offset = 0

# Trạng thái sắp xếp bảng cân bằng
current_sort_column = 'id'
sort_ascending = True
balance_header_rects = []

def restore_main_window():
    global SCREEN
    SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AlgoCards: EDOPro Precise Deck Builder")

def open_duel_vs_ai():
    global current_state
    duel_app = Task4App(on_back_to_menu=restore_main_window)
    if len(user_main_deck) >= duel_app.rules.min_cards:
        duel_app.player_deck = [dict(c) for c in user_main_deck[:duel_app.rules.max_cards]]
        duel_app.start_battle()
    else:
        duel_app.mode = "DECK"
    duel_app.run(return_to_menu=True)
    restore_main_window()
    current_state = GameState.MENU

def get_card_image(card):
    if not card or not card.get('image_url'):
        return None
    card_id = card['id']
    if card_id in image_cache:
        return image_cache[card_id]
    
    if not os.path.exists("card_images"):
        os.makedirs("card_images")
        
    img_path = os.path.join("card_images", f"{card_id}.jpg")
    if not os.path.exists(img_path):
        try:
            urllib.request.urlretrieve(card['image_url'], img_path)
        except Exception:
            pass
            
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

def render_menu():
    draw_honeycomb_bg()
    center_x, center_y = WIDTH // 2, HEIGHT // 2 - 20
    
    points = [(center_x, center_y - 140), (center_x - 150, center_y + 80), (center_x + 150, center_y + 80)]
    pygame.draw.polygon(SCREEN, (35, 10, 10), points)
    pygame.draw.polygon(SCREEN, COLOR_BORDER, points, 3)

    title = FONT_TITLE.render("ALGO CARDS: EDOPro DECK SYSTEM", True, COLOR_ACCENT)
    SCREEN.blit(title, (center_x - title.get_width() // 2, center_y - 105))

    menu_items = [
        ("Deck Builder", GameState.DECK_BUILDER),
        ("Balance Table", GameState.BALANCE),
        ("Online Duel (VS AI)", GameState.BATTLE),
        ("Exit Game", "EXIT")
    ]

    start_y = center_y - 40
    for idx, (text, action) in enumerate(menu_items):
        rect = pygame.Rect(center_x - 130, start_y + idx * 48, 260, 38)
        is_hover = rect.collidepoint(pygame.mouse.get_pos())
        
        color = COLOR_PANEL_HOVER if is_hover else COLOR_PANEL
        pygame.draw.rect(SCREEN, color, rect, border_radius=6)
        pygame.draw.rect(SCREEN, COLOR_BORDER, rect, 1, border_radius=6)
        
        txt_surf = FONT_BOLD.render(text, True, COLOR_TEXT)
        SCREEN.blit(txt_surf, (rect.x + rect.width // 2 - txt_surf.get_width() // 2, rect.y + 10))

def render_balance_table():
    draw_honeycomb_bg()
    global balance_scroll_offset, balance_header_rects
    balance_header_rects = []
    
    panel = pygame.Rect(WIDTH // 2 - 400, 30, 800, HEIGHT - 60)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    pygame.draw.rect(SCREEN, COLOR_BORDER, panel, 2, border_radius=8)

    title = FONT_TITLE.render("BẢNG CÂN BẰNG HỆ THỐNG THẺ BÀI", True, COLOR_ACCENT)
    SCREEN.blit(title, (panel.x + panel.width // 2 - title.get_width() // 2, panel.y + 15))

    total_cards = len(ALL_CARDS)
    avg_cost = sum(c.get('cost', 0) for c in ALL_CARDS) / total_cards if total_cards > 0 else 0
    avg_atk = sum(c.get('ATK', 0) for c in ALL_CARDS) / total_cards if total_cards > 0 else 0
    avg_def = sum(c.get('DEF', 0) for c in ALL_CARDS) / total_cards if total_cards > 0 else 0
    
    max_atk_card = max(ALL_CARDS, key=lambda x: x.get('ATK', 0)) if ALL_CARDS else None
    min_cost_card = min(ALL_CARDS, key=lambda x: x.get('cost', 0)) if ALL_CARDS else None

    stats_y = panel.y + 50
    lines = [
        f"• Tổng số lượng: {total_cards} thẻ  |  Cost TB: {avg_cost:.2f}  |  ATK TB: {avg_atk:.1f}  |  DEF TB: {avg_def:.1f}",
        f"• Thẻ ATK cao nhất: {max_atk_card['name'] if max_atk_card else 'N/A'} ({max_atk_card.get('ATK', 0)} ATK)  |  Thẻ Cost thấp nhất: {min_cost_card['name'] if min_cost_card else 'N/A'} (Cost {min_cost_card.get('cost', 0)})",
    ]
    for line in lines:
        txt = FONT.render(line, True, COLOR_TEXT)
        SCREEN.blit(txt, (panel.x + 30, stats_y))
        stats_y += 22

    table_rect = pygame.Rect(panel.x + 25, stats_y + 10, panel.width - 50, panel.bottom - stats_y - 65)
    
    SCREEN.set_clip(table_rect)
    
    headers = [
        ("Tên Thẻ Bài", 20, 280, 'name'), 
        ("Loại (Category)", 300, 170, 'category'), 
        ("Cost", 480, 70, 'cost'), 
        ("ATK", 560, 70, 'ATK'), 
        ("DEF", 640, 70, 'DEF')
    ]
    hy = table_rect.y + 10
    
    pygame.draw.rect(SCREEN, (30, 20, 25), pygame.Rect(table_rect.x, table_rect.y, table_rect.width, 30), border_radius=4)
    
    for h_text, h_offset, h_width, key in headers:
        col_rect = pygame.Rect(table_rect.x + h_offset, table_rect.y, h_width, 30)
        balance_header_rects.append((col_rect, key))
        
        display_h_text = h_text
        if current_sort_column == key:
            display_h_text += " ▼" if sort_ascending else " ▲"
            
        SCREEN.blit(FONT_BOLD.render(display_h_text, True, COLOR_ACCENT if current_sort_column == key else COLOR_TEXT), (table_rect.x + h_offset, hy))
        
    pygame.draw.line(SCREEN, COLOR_BORDER, (table_rect.x + 10, hy + 22), (table_rect.right - 10, hy + 22), 1)

    # Sắp xếp danh sách thẻ theo cột đang chọn
    sorted_cards = sorted(ALL_CARDS, key=lambda x: x.get(current_sort_column, 0) if current_sort_column in ['cost', 'ATK', 'DEF'] else str(x.get(current_sort_column, '')), reverse=not sort_ascending)

    ty = hy + 32 - balance_scroll_offset
    for idx, card in enumerate(sorted_cards):
        row_y = ty + idx * 28
        if table_rect.y + 25 < row_y < table_rect.bottom:
            SCREEN.blit(FONT.render(card['name'][:30], True, COLOR_TEXT), (table_rect.x + 20, row_y))
            SCREEN.blit(FONT.render(card.get('category', 'N/A')[:20], True, (200, 200, 200)), (table_rect.x + 300, row_y))
            SCREEN.blit(FONT.render(str(card.get('cost', 0)), True, COLOR_TEXT), (table_rect.x + 480, row_y))
            SCREEN.blit(FONT.render(str(card.get('ATK', 0)), True, COLOR_TEXT), (table_rect.x + 560, row_y))
            SCREEN.blit(FONT.render(str(card.get('DEF', 0)), True, COLOR_TEXT), (table_rect.x + 640, row_y))

    SCREEN.set_clip(None)
    
    pygame.draw.rect(SCREEN, COLOR_BORDER, table_rect, 1, border_radius=6)

    note = FONT.render("Nhấn [ESC] về Menu.", True, (180, 180, 180))
    SCREEN.blit(note, (panel.x + panel.width // 2 - note.get_width() // 2, panel.bottom - 30))

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

def render_deck_builder():
    draw_honeycomb_bg()
    global right_list_rects, main_deck_rects, extra_deck_rects, side_deck_rects
    right_list_rects = []
    main_deck_rects = []
    extra_deck_rects = []
    side_deck_rects = []

    # --- 1. KHUNG BÊN TRÁI: CARD PREVIEW ---
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
        
        desc_text = selected_card.get('effect', 'Không có mô tả.')
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

    # --- 2. KHUNG Ở GIỮA: MAIN DECK, EXTRA DECK, SIDE DECK ---
    center_panel = pygame.Rect(320, 15, 620, HEIGHT - 30)
    pygame.draw.rect(SCREEN, (25, 25, 35), center_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, center_panel, 1, border_radius=6)

    top_tools = pygame.Rect(335, 25, 590, 35)
    pygame.draw.rect(SCREEN, COLOR_PANEL, top_tools, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BORDER, top_tools, 1, border_radius=4)
    SCREEN.blit(FONT_BOLD.render(f"Main Deck: {len(user_main_deck)}/40 | Extra Deck: {len(user_extra_deck)}/15 | Side Deck: {len(user_side_deck)}/15", True, COLOR_TEXT), (345, 32))

    # --- MAIN DECK ---
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

    # --- EXTRA DECK ---
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
        pygame.draw.rect(SCREEN, (70, 30, 30), slot_rect, 1, border_radius=3)
        
        if idx < len(user_extra_deck):
            card = user_extra_deck[idx]
            extra_deck_rects.append((slot_rect, idx))
            render_card_thumbnail(c_x, c_y, 48, 52, card)

    # --- SIDE DECK ---
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
        pygame.draw.rect(SCREEN, (70, 30, 30), slot_rect, 1, border_radius=3)
        
        if idx < len(user_side_deck):
            card = user_side_deck[idx]
            side_deck_rects.append((slot_rect, idx))
            render_card_thumbnail(c_x, c_y, 48, 52, card)

    # --- 3. KHUNG BÊN PHẢI: TÌM KIẾM & DANH SÁCH THẺ CÓ CLIP ---
    right_panel = pygame.Rect(955, 15, 310, HEIGHT - 30)
    pygame.draw.rect(SCREEN, COLOR_PANEL, right_panel, border_radius=6)
    pygame.draw.rect(SCREEN, COLOR_BORDER, right_panel, 1, border_radius=6)

    # Ô tìm kiếm (Vẽ cố định phía trên)
    search_box_rect = pygame.Rect(970, 30, 280, 32)
    bg_search = (70, 20, 20) if search_active else (40, 40, 50)
    pygame.draw.rect(SCREEN, bg_search, search_box_rect, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_ACCENT if search_active else COLOR_BORDER, search_box_rect, 1, border_radius=4)
    
    display_text = search_query if search_query else "Nhập tên card để tìm..."
    txt_col = COLOR_TEXT if search_query else (150, 150, 150)
    SCREEN.blit(FONT.render(display_text, True, txt_col), (search_box_rect.x + 10, search_box_rect.y + 7))

    filtered_cards = [c for c in ALL_CARDS if not search_query.strip() or search_query.lower() in c.get('name', '').lower()]

    results_header = pygame.Rect(970, 70, 280, 30)
    pygame.draw.rect(SCREEN, (30, 10, 10), results_header, border_radius=4)
    SCREEN.blit(FONT.render(f"Kết quả ({len(filtered_cards)}) - Kéo thả vào Deck", True, COLOR_ACCENT), (980, 76))

    # --- VÙNG HIỂN THỊ DANH SÁCH THẺ (CÓ CLIP KHÔNG BỊ TRÀN) ---
    list_clip_rect = pygame.Rect(970, 105, 280, HEIGHT - 130)
    SCREEN.set_clip(list_clip_rect)

    ry = 110 - scroll_offset
    for idx, card in enumerate(filtered_cards): 
        if list_clip_rect.y - 60 < ry < list_clip_rect.bottom:
            item_rect = pygame.Rect(970, ry, 280, 52)
            is_sel = (selected_card and selected_card['id'] == card['id'])
            right_list_rects.append((item_rect, card))
            
            render_card_thumbnail(970, ry, 38, 52, card, is_selected=is_sel)
            
            name_surf = FONT_BOLD.render(card['name'][:24], True, COLOR_TEXT)
            info_surf = FONT.render(f"ATK: {card.get('ATK', 0)} / DEF: {card.get('DEF', 0)}", True, (200, 200, 200))
            SCREEN.blit(name_surf, (1018, ry + 6))
            SCREEN.blit(info_surf, (1018, ry + 28))
            
        ry += 56

    SCREEN.set_clip(None)  # Hủy clip

    if dragging_card:
        m_pos = pygame.mouse.get_pos()
        render_card_thumbnail(m_pos[0] - 20, m_pos[1] - 30, 40, 56, dragging_card, is_selected=True)

def render_battle_field():
    draw_honeycomb_bg()
    SCREEN.blit(FONT_TITLE.render("BATTLE MODE: Đang phát triển (Nhấn ESC về Menu)", True, COLOR_ACCENT), (WIDTH//2 - 300, HEIGHT//2))

async def main():
    global current_state, selected_card, user_main_deck, user_extra_deck, user_side_deck, search_query, search_active, dragging_card, scroll_offset, balance_scroll_offset, current_sort_column, sort_ascending
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if current_state == GameState.DECK_BUILDER and mouse_pos[0] > 955: 
                    scroll_offset -= event.y * 30
                    scroll_offset = max(0, scroll_offset)
                elif current_state == GameState.BALANCE:
                    balance_scroll_offset -= event.y * 25
                    balance_scroll_offset = max(0, min(balance_scroll_offset, 250))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                center_x, center_y = WIDTH // 2, HEIGHT // 2 - 20
                
                if current_state == GameState.MENU:
                    if pygame.Rect(center_x - 130, center_y - 40, 260, 38).collidepoint(mouse_pos):
                        current_state = GameState.DECK_BUILDER
                    elif pygame.Rect(center_x - 130, center_y + 8, 260, 38).collidepoint(mouse_pos):
                        current_state = GameState.BALANCE
                    elif pygame.Rect(center_x - 130, center_y + 56, 260, 38).collidepoint(mouse_pos):
                        open_duel_vs_ai()
                    elif pygame.Rect(center_x - 130, center_y + 104, 260, 38).collidepoint(mouse_pos):
                        running = False
                
                elif current_state == GameState.BALANCE:
                    # Kiểm tra click vào tiêu đề cột để sắp xếp
                    for rect, key in balance_header_rects:
                        if rect.collidepoint(mouse_pos):
                            if current_sort_column == key:
                                sort_ascending = not sort_ascending
                            else:
                                current_sort_column = key
                                sort_ascending = True
                
                elif current_state == GameState.DECK_BUILDER:
                    search_box_rect = pygame.Rect(970, 30, 280, 32)
                    if search_box_rect.collidepoint(mouse_pos):
                        search_active = True
                    else:
                        search_active = False

                    for rect, card in right_list_rects:
                        if rect.collidepoint(mouse_pos):
                            selected_card = card
                            dragging_card = card

                    for rect, idx in main_deck_rects:
                        if rect.collidepoint(mouse_pos):
                            if idx < len(user_main_deck):
                                removed = user_main_deck.pop(idx)
                                print(f"[DECK] Đã xóa '{removed['name']}' khỏi Main Deck.")

                    for rect, idx in extra_deck_rects:
                        if rect.collidepoint(mouse_pos):
                            if idx < len(user_extra_deck):
                                removed = user_extra_deck.pop(idx)
                                print(f"[DECK] Đã xóa '{removed['name']}' khỏi Extra Deck.")

                    for rect, idx in side_deck_rects:
                        if rect.collidepoint(mouse_pos):
                            if idx < len(user_side_deck):
                                removed = user_side_deck.pop(idx)
                                print(f"[DECK] Đã xóa '{removed['name']}' khỏi Side Deck.")

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if current_state == GameState.DECK_BUILDER and dragging_card:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    main_deck_box = pygame.Rect(335, 68, 590, 315)
                    extra_box = pygame.Rect(335, 390, 590, 140)
                    side_box = pygame.Rect(335, 538, 590, 140)

                    if main_deck_box.collidepoint(mouse_pos):
                        success, message = deck_manager.add_card(dragging_card)
                        if success:
                            print(f"[DECK] {message}")
                        else:
                            print(f"[WARNING] {message}")
                            
                    elif extra_box.collidepoint(mouse_pos):
                        if len(user_extra_deck) < 15:
                            # Đếm số lượng thẻ trùng id trong Extra Deck (giới hạn tối đa 3 con)
                            same_card_count = sum(1 for c in user_extra_deck if c['id'] == dragging_card['id'])
                            if same_card_count < 3:
                                user_extra_deck.append(dragging_card)
                                print(f"[DECK] Đã thêm vào Extra Deck: {dragging_card['name']}")
                            else:
                                print(f"[WARNING] Extra Deck đã đạt tối đa 3 bản sao của thẻ này!")
                        else:
                            print(f"[WARNING] Extra Deck đã đầy (tối đa 15 lá)!")
                            
                    elif side_box.collidepoint(mouse_pos):
                        if len(user_side_deck) < 15:
                            # Đếm số lượng thẻ trùng id trong Side Deck (giới hạn tối đa 3 con)
                            same_card_count = sum(1 for c in user_side_deck if c['id'] == dragging_card['id'])
                            if same_card_count < 3:
                                user_side_deck.append(dragging_card)
                                print(f"[DECK] Đã thêm vào Side Deck: {dragging_card['name']}")
                            else:
                                print(f"[WARNING] Side Deck đã đạt tối đa 3 bản sao của thẻ này!")
                        else:
                            print(f"[WARNING] Side Deck đã đầy (tối đa 15 lá)!")
                            
                    dragging_card = None

            if event.type == pygame.KEYDOWN:
                if current_state == GameState.DECK_BUILDER and search_active:
                    if event.key == pygame.K_BACKSPACE:
                        search_query = search_query[:-1]
                    elif event.key == pygame.K_RETURN:
                        search_active = False
                    else:
                        if event.unicode.isprintable():
                            search_query += event.unicode
                            scroll_offset = 0
                
                if event.key == pygame.K_ESCAPE:
                    current_state = GameState.MENU

        if current_state == GameState.MENU:
            render_menu()
        elif current_state == GameState.DECK_BUILDER:
            render_deck_builder()
        elif current_state == GameState.BALANCE:
            render_balance_table()
        elif current_state == GameState.BATTLE:
            render_battle_field()

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())