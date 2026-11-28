import random
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame

from ai_replay import HeuristicAI, ReplayRecorder
from pygame_ui import (
    Button,
    HorizontalSlider,
    ImageCache,
    draw_wrapped_text,
    load_cards_data,
    load_vietnamese_font,
)
from task4_manager import DeckRules, LeaderboardManager, TutorialManager, summarize_deck

WIDTH, HEIGHT = 1280, 760
FPS = 60


class Task4App:
    def __init__(self, on_back_to_menu: Optional[Callable[[], None]] = None):
        pygame.init()
        pygame.display.set_caption("Task 4 - Deck Builder, Tutorial, Heuristic AI, Replay & Leaderboard")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.on_back_to_menu = on_back_to_menu

        self.font_title = load_vietnamese_font(22, bold=True)
        self.font_ui = load_vietnamese_font(15, bold=True)
        self.font_small = load_vietnamese_font(13, bold=False)

        self.all_cards = load_cards_data("cards.json")
        self.images = ImageCache("card_images")
        self.rules = DeckRules(min_cards=8, max_cards=20, max_copies=3)
        self.tutorial = TutorialManager()
        self.leaderboard = LeaderboardManager("leaderboard.json")
        self.replay = ReplayRecorder("last_replay.json")

        self.player_deck: List[Dict[str, Any]] = (
            [dict(self.all_cards[i % len(self.all_cards)]) for i in range(min(10, len(self.all_cards)))]
            if self.all_cards
            else []
        )
        self.ai = HeuristicAI("Heuristic AI", self.all_cards)

        self.mode = "DECK"
        self.status_msg = "Kéo thẻ hoặc click để thêm vào Deck (8 - 20 lá, tối đa 3 bản/thẻ)."
        self.pool_scroll = 0

        self.dragging = False
        self.drag_card: Optional[Dict[str, Any]] = None
        self.drag_pos = (0, 0)
        self.drag_offset = (0, 0)
        self.pool_card_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []

        self.turn = 1
        self.player_hp = 8000
        self.player_mana = 10
        self.player_hand: List[Dict[str, Any]] = []
        self.player_field: List[Dict[str, Any]] = []
        self.battle_log: List[str] = []
        self.battle_over = False
        self.hand_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []
        self.field_rects: List[Tuple[pygame.Rect, Dict[str, Any], bool]] = []

        self.hand_scroll = 0
        self.hand_slider = HorizontalSlider((24, 678, 756, 16))
        self.hand_btn_prev = pygame.Rect(24, 496, 30, 22)
        self.hand_btn_next = pygame.Rect(750, 496, 30, 22)

        self.replay_data: Dict[str, Any] = {"meta": {}, "actions": []}
        self.replay_step = 0
        self.replay_scroll = 0

        self.nav_buttons = {
            "MENU": Button((20, 14, 130, 36), "← Menu chính", bg=(110, 55, 55)),
            "DECK": Button((160, 14, 150, 36), "1. Deck Builder"),
            "BATTLE": Button((320, 14, 140, 36), "2. Đấu AI"),
            "REPLAY": Button((470, 14, 130, 36), "3. Replay"),
            "LEADERBOARD": Button((610, 14, 155, 36), "4. Leaderboard"),
            "TUTORIAL": Button((775, 14, 120, 36), "Tutorial", bg=(38, 110, 95)),
        }
        self.btn_auto_fill = Button((20, 695, 165, 38), "Tự động điền Deck")
        self.btn_clear_deck = Button((195, 695, 135, 38), "Xóa Deck", bg=(125, 48, 48))
        self.btn_start_battle = Button((340, 695, 180, 38), "Vào trận đấu AI", bg=(35, 115, 70))
        self.btn_end_turn = Button((1060, 680, 180, 40), "Kết thúc lượt", bg=(140, 85, 35))
        self.btn_restart_battle = Button((860, 680, 180, 40), "Đấu lại", bg=(45, 95, 155))
        self.btn_replay_next = Button((220, 685, 170, 40), "Bước tiếp theo", bg=(35, 115, 70))
        self.btn_replay_prev = Button((40, 685, 170, 40), "Lùi 1 bước")

    def _get_max_hand_scroll(self) -> int:
        return max(0, len(self.player_hand) * 165 - 10 - 756)

    def _record_event(self, phase: str, player: str, action_type: str, line: str):
        self.battle_log.append(line)
        self.replay.log(
            self.turn,
            phase,
            player,
            action_type,
            {
                "text": line,
                "player_hp": self.player_hp,
                "ai_hp": self.ai.hp,
            },
        )
        self._finish_battle_if_needed()

    def start_battle(self):
        ok, msg = self.rules.is_valid_to_battle(self.player_deck)
        if not ok:
            self.status_msg = msg
            return
        if not self.all_cards:
            self.status_msg = "Không tìm thấy dữ liệu thẻ trong card.json / cards.json."
            return

        p_pool = [dict(c) for c in self.player_deck]
        random.shuffle(p_pool)
        ai_pool = [dict(c) for c in random.sample(self.all_cards, k=min(len(self.all_cards), max(8, len(self.player_deck))))]
        random.shuffle(ai_pool)

        self.turn = 1
        self.player_hp = 8000
        self.player_mana = 10
        self.player_hand = list(p_pool)
        self.player_field = []
        self.hand_scroll = 0
        self.battle_over = False
        self.mode = "BATTLE"

        self.ai = HeuristicAI("Heuristic AI", ai_pool)
        self.ai.hp = 8000
        self.ai.max_mana = 10
        self.ai.mana = 10
        self.ai.hand = list(ai_pool[:4])
        self.ai.field = []

        self.battle_log = ["Trận đấu bắt đầu! Mana khởi đầu 10 (+2 mỗi lượt). Trượt/cuộn để chọn bài."]
        self.replay.start_match([c["name"] for c in self.player_deck], [c["name"] for c in ai_pool])

    def _finish_battle_if_needed(self):
        if self.battle_over:
            return
        if self.ai.hp <= 0:
            self.ai.hp = 0
            self.battle_over = True
            msg = "Bạn CHIẾN THẮNG Heuristic AI!"
            self.battle_log.append(msg)
            self.replay.log(self.turn, "END", "SYSTEM", "WIN", {"text": msg, "player_hp": self.player_hp, "ai_hp": 0})
            self.replay.save_file("PLAYER_WIN", self.player_hp, 0)
            self.leaderboard.record_result("Player_1", True, self.player_hp)
        elif self.player_hp <= 0:
            self.player_hp = 0
            self.battle_over = True
            msg = "Heuristic AI CHIẾN THẮNG!"
            self.battle_log.append(msg)
            self.replay.log(self.turn, "END", "SYSTEM", "LOSE", {"text": msg, "player_hp": 0, "ai_hp": self.ai.hp})
            self.replay.save_file("AI_WIN", 0, self.ai.hp)
            self.leaderboard.record_result("Player_1", False, 0)

    def _resolve_combat(
        self,
        attacker: Dict[str, Any],
        attacker_side: str,
        defender_field: List[Dict[str, Any]],
    ) -> str:
        atk = max(0, int(attacker.get("ATK", 0)))
        if atk <= 0:
            return f"{attacker['name']} có 0 ATK, không thể tấn công."

        is_player = attacker_side == "PLAYER"
        prefix = "" if is_player else "AI dùng "

        if not defender_field:
            if is_player:
                self.ai.hp -= atk
            else:
                self.player_hp -= atk
            return f"[Turn {self.turn}] {prefix}{attacker['name']} (ATK {atk}) đánh thẳng (-{atk} HP)."

        target = defender_field[0]
        t_atk = max(0, int(target.get("ATK", 0)))
        t_def = max(0, int(target.get("DEF", 0)))

        if target.get("_defense_mode"):
            if atk > t_def:
                defender_field.remove(target)
                return f"[Turn {self.turn}] {prefix}{attacker['name']} (ATK {atk}) phá thủ {target['name']} (DEF {t_def})."
            if atk == t_def:
                return f"[Turn {self.turn}] {attacker['name']} (ATK {atk}) ngang thủ {target['name']} (DEF {t_def})."
            dmg = t_def - atk
            if is_player:
                self.player_hp -= dmg
            else:
                self.ai.hp -= dmg
            return f"[Turn {self.turn}] {target['name']} (DEF {t_def}) thủ vững trước {attacker['name']} (ATK {atk}) (-{dmg} HP)."

        if atk > t_atk:
            dmg = atk - t_atk
            defender_field.remove(target)
            if is_player:
                self.ai.hp -= dmg
            else:
                self.player_hp -= dmg
            return f"[Turn {self.turn}] {prefix}{attacker['name']} (ATK {atk}) hạ {target['name']} (ATK {t_atk}) (-{dmg} HP)."

        if atk == t_atk:
            defender_field.remove(target)
            own_field = self.player_field if is_player else self.ai.field
            if attacker in own_field:
                own_field.remove(attacker)
            return f"[Turn {self.turn}] {attacker['name']} (ATK {atk}) và {target['name']} (ATK {t_atk}) đồng quy tận!"

        dmg = t_atk - atk
        own_field = self.player_field if is_player else self.ai.field
        if attacker in own_field:
            own_field.remove(attacker)
        if is_player:
            self.player_hp -= dmg
        else:
            self.ai.hp -= dmg
        return f"[Turn {self.turn}] {prefix}{attacker['name']} (ATK {atk}) yếu hơn {target['name']} (ATK {t_atk}) bị hạ (-{dmg} HP)."

    def play_player_card(self, card: Dict[str, Any]):
        if self.battle_over:
            return
        cost = int(card.get("cost", 1))
        if cost > self.player_mana:
            self.battle_log.append(f"Không đủ Mana ({self.player_mana}/{cost}) cho {card['name']}.")
            return
        if len(self.player_field) >= 4:
            self.battle_log.append("Sân của bạn đã đủ 4 thẻ!")
            return

        self.player_hand.remove(card)
        self.hand_scroll = min(self.hand_scroll, self._get_max_hand_scroll())
        self.player_mana -= cost
        unit = dict(card)
        unit["_attacked"] = False
        unit["_defense_mode"] = False
        self.player_field.append(unit)
        self._record_event(
            "MAIN",
            "PLAYER",
            "SUMMON",
            f"[Turn {self.turn}] Bạn ra {unit['name']} (Cost {cost}, ATK {unit['ATK']}/DEF {unit['DEF']}).",
        )

    def player_attack(self, unit: Dict[str, Any]):
        if self.battle_over or unit.get("_attacked") or unit not in self.player_field:
            return
        if int(unit.get("ATK", 0)) <= 0:
            self.battle_log.append(f"{unit['name']} có 0 ATK, không thể tấn công.")
            return
        unit["_attacked"] = True
        line = self._resolve_combat(unit, "PLAYER", self.ai.field)
        self._record_event("BATTLE", "PLAYER", "ATTACK", line)

    def run_ai_turn(self):
        if self.battle_over:
            return
        # Sang lượt AI: +2 vào số mana hiện tại của AI (nếu là lượt AI đầu tiên thì giữ 10 hoặc +2 tùy ý)
        self.ai.mana += 2
        self.ai.max_mana = self.ai.mana
        for u in self.ai.field:
            u["_attacked"] = False

        if self.ai.hand and self.all_cards and len(self.ai.hand) < 6:
            self.ai.hand.append(dict(random.choice(self.all_cards)))

        acted = False
        for _ in range(3):
            if self.battle_over:
                break
            card = self.ai.decide_move()
            if card is not None and len(self.ai.field) < 4 and card in self.ai.hand:
                cost = int(card.get("cost", 0))
                self.ai.hand.remove(card)
                self.ai.mana -= cost
                unit = dict(card)
                unit["_attacked"] = False
                unit["_defense_mode"] = int(unit.get("DEF", 0)) > int(unit.get("ATK", 0)) + 400
                self.ai.field.append(unit)
                acted = True
                mode_lbl = "THỦ" if unit["_defense_mode"] else "CÔNG"
                self._record_event(
                    "MAIN",
                    self.ai.username,
                    "SUMMON",
                    f"[Turn {self.turn}] AI ra {unit['name']} [{mode_lbl}] (Cost {cost}, ATK {unit['ATK']}/DEF {unit['DEF']}).",
                )
                continue

            attacker = self.ai.pick_attacker()
            if attacker is not None:
                attacker["_attacked"] = True
                acted = True
                self._record_event("BATTLE", self.ai.username, "ATTACK", self._resolve_combat(attacker, "AI", self.player_field))
                continue

            break

        if not acted:
            self.battle_log.append(f"[Turn {self.turn}] AI kết thúc lượt (Mana: {self.ai.mana}/{self.ai.max_mana}).")

        if not self.battle_over:
            self.turn += 1
            # Sang lượt mới của người chơi: +2 vào số mana hiện tại
            self.player_mana += 2
            for u in self.player_field:
                u["_attacked"] = False
            self.battle_log.append(f"--- Bắt đầu Turn {self.turn} (Mana: {self.player_mana}) ---")

    def handle_events(self, return_to_menu: bool = False) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if return_to_menu and self.on_back_to_menu:
                    self.on_back_to_menu()
                    return False
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEWHEEL:
                if self.mode == "DECK":
                    self.pool_scroll = max(0, min(max(0, len(self.all_cards) - 6), self.pool_scroll - event.y * 2))
                elif self.mode == "BATTLE":
                    self.hand_scroll = max(0, min(self._get_max_hand_scroll(), self.hand_scroll - event.y * 90))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.tutorial.active:
                    if pygame.Rect(WIDTH // 2 + 40, HEIGHT // 2 + 95, 140, 38).collidepoint(pos):
                        self.tutorial.next_step()
                    elif pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 95, 140, 38).collidepoint(pos):
                        self.tutorial.prev_step()
                    elif pygame.Rect(WIDTH // 2 + 210, HEIGHT // 2 - 135, 36, 36).collidepoint(pos):
                        self.tutorial.close()
                    continue

                if self.nav_buttons["MENU"].clicked(pos):
                    if return_to_menu and self.on_back_to_menu:
                        self.on_back_to_menu()
                        return False
                    self.mode = "DECK"
                    continue

                if self.nav_buttons["TUTORIAL"].clicked(pos):
                    self.tutorial.open()
                    continue

                for key in ("DECK", "BATTLE", "REPLAY", "LEADERBOARD"):
                    if self.nav_buttons[key].clicked(pos):
                        if key == "BATTLE":
                            self.start_battle()
                        elif key == "REPLAY":
                            self.replay_data = self.replay.load_file()
                            self.replay_step = 0
                            self.mode = "REPLAY"
                        else:
                            self.mode = key
                        break

                if self.mode == "DECK":
                    if self.btn_auto_fill.clicked(pos) and self.all_cards:
                        self.player_deck = [
                            dict(self.all_cards[i % len(self.all_cards)])
                            for i in range(min(self.rules.max_cards, max(self.rules.min_cards, 12)))
                        ]
                        self.status_msg = f"Đã tự động tạo Deck {len(self.player_deck)} lá."
                    elif self.btn_clear_deck.clicked(pos):
                        self.player_deck.clear()
                        self.status_msg = "Đã xóa toàn bộ thẻ trong Deck."
                    elif self.btn_start_battle.clicked(pos):
                        self.start_battle()
                    else:
                        for rect, card in self.pool_card_rects:
                            if rect.collidepoint(pos):
                                self.dragging = True
                                self.drag_card, self.drag_pos = card, pos
                                self.drag_offset = (rect.x - pos[0], rect.y - pos[1])
                                break

                elif self.mode == "BATTLE":
                    max_s = self._get_max_hand_scroll()
                    jumped = self.hand_slider.handle_mouse_down(pos, max_s)
                    if jumped is not None:
                        self.hand_scroll = jumped
                    elif self.hand_btn_prev.collidepoint(pos):
                        self.hand_scroll = max(0, self.hand_scroll - 165)
                    elif self.hand_btn_next.collidepoint(pos):
                        self.hand_scroll = min(max_s, self.hand_scroll + 165)
                    elif self.btn_end_turn.clicked(pos):
                        self.run_ai_turn()
                    elif self.btn_restart_battle.clicked(pos):
                        self.start_battle()
                    else:
                        for rect, card in self.hand_rects:
                            if rect.collidepoint(pos):
                                self.play_player_card(card)
                                break
                        for rect, unit, attacked in self.field_rects:
                            if rect.collidepoint(pos) and not attacked:
                                self.player_attack(unit)
                                break

                elif self.mode == "REPLAY":
                    actions = self.replay_data.get("actions", [])
                    if self.btn_replay_next.clicked(pos) and self.replay_step < len(actions):
                        self.replay_step += 1
                    elif self.btn_replay_prev.clicked(pos) and self.replay_step > 0:
                        self.replay_step -= 1

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.drag_pos = event.pos
                elif self.mode == "BATTLE":
                    moved = self.hand_slider.handle_mouse_move(event.pos[0], self._get_max_hand_scroll())
                    if moved is not None:
                        self.hand_scroll = moved

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.hand_slider.dragging = False
                if self.dragging and self.drag_card is not None:
                    drop_zone = pygame.Rect(780, 75, 480, 600)
                    if drop_zone.collidepoint(event.pos) or (
                        abs(event.pos[0] - self.drag_pos[0]) < 6 and abs(event.pos[1] - self.drag_pos[1]) < 6
                    ):
                        ok, msg = self.rules.can_add_card(self.player_deck, self.drag_card)
                        if ok:
                            self.player_deck.append(dict(self.drag_card))
                            self.status_msg = f"Đã thêm '{self.drag_card['name']}' ({len(self.player_deck)}/{self.rules.max_cards})."
                        else:
                            self.status_msg = msg
                    self.dragging = False
                    self.drag_card = None

        return True

    def draw_card_box(self, rect: pygame.Rect, card: Dict[str, Any], highlight: bool = False):
        pygame.draw.rect(self.screen, (34, 43, 60), rect, border_radius=8)
        pygame.draw.rect(self.screen, (235, 190, 75) if highlight else (100, 125, 165), rect, width=2, border_radius=8)
        img_w, img_h = rect.width - 16, max(42, int(rect.height * 0.40))
        img_rect = pygame.Rect(rect.x + 8, rect.y + 8, img_w, img_h)
        art = self.images.get(card, (img_w, img_h))
        if art:
            self.screen.blit(art, img_rect.topleft)
        else:
            pygame.draw.rect(self.screen, (52, 66, 92), img_rect, border_radius=4)

        ty = img_rect.bottom + 5
        self.screen.blit(self.font_small.render(card["name"][:25], True, (245, 248, 252)), (rect.x + 8, ty))
        ty += 17
        self.screen.blit(
            self.font_small.render(f"[{card['category']}] C:{card['cost']} A:{card['ATK']} D:{card['DEF']}", True, (150, 215, 255)),
            (rect.x + 8, ty),
        )
        draw_wrapped_text(self.screen, card.get("effect", ""), self.font_small, (205, 214, 226), rect.x + 8, ty + 17, rect.width - 16, rect.bottom - 6)

    def render_deck_mode(self):
        self.pool_card_rects.clear()
        pygame.draw.rect(self.screen, (25, 33, 46), (20, 75, 740, 600), border_radius=8)
        self.screen.blit(self.font_ui.render("Kho thẻ thuật toán (Kéo sang phải hoặc Click để thêm - Cuộn chuột xem thêm)", True, (220, 232, 248)), (34, 86))

        for idx, card in enumerate(self.all_cards[self.pool_scroll : self.pool_scroll + 6]):
            r = pygame.Rect(36 + (idx % 3) * 240, 118 + (idx // 3) * 270, 225, 255)
            self.draw_card_box(r, card)
            self.pool_card_rects.append((r, card))

        deck_rect = pygame.Rect(780, 75, 480, 600)
        pygame.draw.rect(self.screen, (28, 38, 54), deck_rect, border_radius=8)
        pygame.draw.rect(self.screen, (85, 150, 220), deck_rect, width=2, border_radius=8)

        stats = summarize_deck(self.player_deck)
        self.screen.blit(
            self.font_ui.render(f"Deck của bạn: {stats['count']}/{self.rules.max_cards} lá (Min {self.rules.min_cards}) | Avg Cost: {stats['avg_cost']}", True, (240, 245, 255)),
            (795, 88),
        )
        self.screen.blit(
            self.font_small.render(" | ".join(f"{k}:{v}" for k, v in stats["categories"].items()) or "Chưa có thẻ", True, (155, 210, 180)),
            (795, 114),
        )

        ly = 144
        for idx, c in enumerate(self.player_deck):
            if ly > 640:
                break
            self.screen.blit(self.font_small.render(f"{idx + 1}. {c['name']} ({c['category']}) - Cost {c['cost']} | ATK {c['ATK']} / DEF {c['DEF']}", True, (225, 232, 240)), (798, ly))
            ly += 22

        self.btn_auto_fill.draw(self.screen, self.font_ui)
        self.btn_clear_deck.draw(self.screen, self.font_ui)
        self.btn_start_battle.draw(self.screen, self.font_ui)
        self.screen.blit(self.font_ui.render(self.status_msg, True, (255, 215, 110)), (535, 703))

        if self.dragging and self.drag_card is not None:
            self.draw_card_box(pygame.Rect(self.drag_pos[0] + self.drag_offset[0], self.drag_pos[1] + self.drag_offset[1], 210, 235), self.drag_card, highlight=True)

    def render_battle_mode(self):
        self.hand_rects.clear()
        self.field_rects.clear()

        self.screen.blit(
            self.font_title.render(
                f"Turn {self.turn} | Player HP: {self.player_hp} (Mana: {self.player_mana})  VS  {self.ai.username} HP: {self.ai.hp} (Mana: {self.ai.mana})",
                True,
                (245, 248, 252),
            ),
            (24, 72),
        )
        self.screen.blit(self.font_ui.render("Sân AI:", True, (255, 150, 150)), (24, 112))
        for i, u in enumerate(self.ai.field):
            self.draw_card_box(pygame.Rect(24 + i * 185, 136, 175, 155), u)

        self.screen.blit(self.font_ui.render("Sân của bạn (Click quái để tấn công):", True, (140, 235, 175)), (24, 305))
        for i, u in enumerate(self.player_field):
            r = pygame.Rect(24 + i * 185, 330, 175, 155)
            self.draw_card_box(r, u, highlight=not u.get("_attacked"))
            self.field_rects.append((r, u, bool(u.get("_attacked"))))

        self.screen.blit(self.font_ui.render(f"Bộ bài / Tay bài ({len(self.player_hand)} lá - Trượt hoặc cuộn để chọn):", True, (165, 210, 255)), (60, 496))
        for btn_rect, sym in ((self.hand_btn_prev, "◀"), (self.hand_btn_next, "▶")):
            pygame.draw.rect(self.screen, (45, 58, 82), btn_rect, border_radius=4)
            s = self.font_ui.render(sym, True, (240, 244, 248))
            self.screen.blit(s, s.get_rect(center=btn_rect.center))

        hand_view = pygame.Rect(24, 522, 756, 148)
        max_scroll = self._get_max_hand_scroll()
        self.hand_scroll = max(0, min(max_scroll, self.hand_scroll))

        self.screen.set_clip(hand_view)
        for i, c in enumerate(self.player_hand):
            r = pygame.Rect(24 + i * 165 - self.hand_scroll, 524, 155, 145)
            if r.right >= hand_view.left and r.left <= hand_view.right:
                self.draw_card_box(r, c)
                self.hand_rects.append((r, c))
        self.screen.set_clip(None)

        self.hand_slider.update_thumb(self.hand_scroll, max_scroll, len(self.player_hand))
        self.hand_slider.draw(self.screen)

        pygame.draw.rect(self.screen, (25, 33, 46), (800, 112, 460, 550), border_radius=8)
        self.screen.blit(self.font_ui.render("Nhật ký trận đấu (Lưu Replay)", True, (230, 238, 248)), (816, 124))
        ly = 156
        for entry in self.battle_log[-18:]:
            ly = draw_wrapped_text(self.screen, entry, self.font_small, (210, 222, 235), 816, ly, 430, 645)

        self.btn_end_turn.draw(self.screen, self.font_ui)
        self.btn_restart_battle.draw(self.screen, self.font_ui)

    def render_replay_mode(self):
        meta, actions = self.replay_data.get("meta", {}), self.replay_data.get("actions", [])
        self.screen.blit(
            self.font_title.render(f"Replay - Kết quả: {meta.get('result', 'N/A')} ({self.replay_step}/{len(actions)} bước)", True, (245, 248, 252)),
            (24, 75),
        )
        pygame.draw.rect(self.screen, (25, 33, 46), (24, 120, 1230, 540), border_radius=8)
        y = 140
        for act in actions[: self.replay_step]:
            details = act.get("details", {})
            desc = details.get("text", str(details)) if isinstance(details, dict) else str(details)
            p_hp = details.get("player_hp", "-") if isinstance(details, dict) else "-"
            a_hp = details.get("ai_hp", "-") if isinstance(details, dict) else "-"
            y = draw_wrapped_text(
                self.screen,
                f"[Bước {act['step']} | Turn {act['turn']} | {act['player']}] {desc}  (P_HP: {p_hp} | AI_HP: {a_hp})",
                self.font_ui,
                (215, 230, 245),
                42,
                y,
                1190,
                640,
            )
        self.btn_replay_prev.draw(self.screen, self.font_ui)
        self.btn_replay_next.draw(self.screen, self.font_ui)

    def render_leaderboard_mode(self):
        self.screen.blit(self.font_title.render("Bảng xếp hạng (Leaderboard)", True, (245, 248, 252)), (24, 75))
        pygame.draw.rect(self.screen, (25, 33, 46), (24, 120, 760, 540), border_radius=8)
        y = 145
        for rank, item in enumerate(self.leaderboard.top(10), start=1):
            self.screen.blit(
                self.font_ui.render(f"#{rank}  {item['player']}  —  Điểm: {item['points']}  (Thắng: {item['wins']} | Thua: {item['losses']})", True, (235, 242, 250)),
                (48, y),
            )
            y += 42

    def render_tutorial_modal(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 145, 520, 290)
        pygame.draw.rect(self.screen, (36, 48, 68), panel, border_radius=10)
        pygame.draw.rect(self.screen, (95, 165, 235), panel, width=2, border_radius=10)

        title, desc = self.tutorial.current()
        self.screen.blit(self.font_title.render(title, True, (250, 220, 115)), (panel.x + 24, panel.y + 22))
        draw_wrapped_text(self.screen, desc, self.font_ui, (235, 242, 250), panel.x + 24, panel.y + 72, 470, panel.bottom - 65)

        btns = [
            (pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 95, 140, 38), (65, 82, 110), "Trước"),
            (pygame.Rect(WIDTH // 2 + 40, HEIGHT // 2 + 95, 140, 38), (45, 130, 85), "Hoàn tất" if self.tutorial.index == len(self.tutorial.STEPS) - 1 else "Tiếp theo"),
            (pygame.Rect(WIDTH // 2 + 210, HEIGHT // 2 - 135, 36, 36), (150, 55, 55), "X"),
        ]
        for r, col, lbl in btns:
            pygame.draw.rect(self.screen, col, r, border_radius=6)
            t = self.font_ui.render(lbl, True, (245, 245, 245))
            self.screen.blit(t, t.get_rect(center=r.center))

    def run(self, return_to_menu: bool = False):
        while True:
            if not self.handle_events(return_to_menu=return_to_menu):
                return
            self.screen.fill((18, 24, 34))
            for key, btn in self.nav_buttons.items():
                btn.draw(self.screen, self.font_ui, active=(self.mode == key))

            if self.mode == "DECK":
                self.render_deck_mode()
            elif self.mode == "BATTLE":
                self.render_battle_mode()
            elif self.mode == "REPLAY":
                self.render_replay_mode()
            elif self.mode == "LEADERBOARD":
                self.render_leaderboard_mode()

            if self.tutorial.active:
                self.render_tutorial_modal()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Task4App().run()