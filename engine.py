"""Task 3 - Rule engine và trạng thái trận đấu (Nhóm 3 - GAME 3)."""

START_HP = 4000
START_HAND = 4
MAX_MANA_CAP = 10


class Player:
    def __init__(self, username, deck):
        self.username = username
        self.hp = START_HP
        self.shield = 0          # điểm phòng thủ (DEF) từ thẻ Stack, hấp thụ sát thương trước HP
        self.max_mana = 1
        self.mana = 1
        self.deck = list(deck)
        self.hand = []
        self.field = []
        self.graveyard = []

    def draw_card(self):
        """Rút 1 thẻ từ đỉnh deck. Trả về None nếu deck rỗng."""
        if self.deck:
            card = self.deck.pop(0)
            self.hand.append(card)
            return card
        return None

    def take_damage(self, amount):
        """Sát thương trừ vào shield trước, phần dư trừ vào HP. Trả về HP thực sự bị mất."""
        absorbed = min(self.shield, amount)
        self.shield -= absorbed
        lost = amount - absorbed
        self.hp = max(0, self.hp - lost)
        return lost

    def gain_mana(self, amount):
        self.mana = min(MAX_MANA_CAP, self.mana + amount)

    def to_dict(self):
        return {
            "username": self.username,
            "hp": self.hp,
            "shield": self.shield,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "deck_size": len(self.deck),
            "hand": [c["id"] for c in self.hand],
            "field": [c["id"] for c in self.field],
            "graveyard": [c["id"] for c in self.graveyard],
        }


class GameEngine:
    PHASES = ["DRAW PHASE", "STANDBY PHASE", "MAIN PHASE", "BATTLE PHASE", "END PHASE"]

    def __init__(self, p1_name, p1_deck, p2_name, p2_deck):
        self.player1 = Player(p1_name, p1_deck)
        self.player2 = Player(p2_name, p2_deck)
        self.current_turn_player = self.player1
        self.opponent_player = self.player2
        self.phase_idx = 0
        self.turn_count = 1
        self.game_over = False
        self.winner = None          # None khi chưa kết thúc hoặc hòa
        self.log = []               # nhật ký hành động, Task 4 (replay) có thể dùng lại

        # Tay bài ban đầu (mỗi người tối đa 4 lá)
        for _ in range(START_HAND):
            self.player1.draw_card()
            self.player2.draw_card()

    # ------------------------------------------------------------------ log
    def _log(self, action_type, details):
        self.log.append({
            "turn": self.turn_count,
            "phase": self.current_phase,
            "player": self.current_turn_player.username,
            "action_type": action_type,
            "details": details,
        })

    # ---------------------------------------------------------------- phase
    @property
    def current_phase(self):
        return self.PHASES[self.phase_idx]

    def next_phase(self):
        if self.game_over:
            return "Trận đấu đã kết thúc!"

        self.phase_idx += 1
        if self.phase_idx >= len(self.PHASES):
            self.phase_idx = 0
            self.switch_turn()

        msg = f"Chuyển sang phase: {self.current_phase}"
        self._log("PHASE", msg)
        return msg

    def switch_turn(self):
        # Đổi lượt
        self.current_turn_player, self.opponent_player = self.opponent_player, self.current_turn_player
        self.turn_count += 1

        # Tăng Mana tối đa (tối đa 10) và hồi đầy Mana
        p = self.current_turn_player
        p.max_mana = min(MAX_MANA_CAP, p.max_mana + 1)
        p.mana = p.max_mana

        # Rút bài đầu lượt; hết bài thì thua
        drawn = p.draw_card()
        if drawn is None:
            self.game_over = True
            self.winner = self.opponent_player.username
            self._log("GAME_OVER", f"{p.username} hết bài để rút, {self.winner} thắng.")
        else:
            self._log("DRAW", f"{p.username} rút thẻ [{drawn['name']}].")

    # ----------------------------------------------------------- play card
    def play_card(self, card_id):
        if self.game_over:
            return False, "Trận đấu đã kết thúc!"
        if self.current_phase != "MAIN PHASE":
            return False, "Chỉ được triển khai thẻ bài trong MAIN PHASE!"

        player = self.current_turn_player
        target_card = next((c for c in player.hand if c["id"] == card_id), None)
        if not target_card:
            return False, "Thẻ bài không tồn tại trên tay!"

        cost = target_card.get("cost", 0)
        if player.mana < cost:
            return False, f"Không đủ Mana! Cần {cost} Mana nhưng chỉ còn {player.mana}."

        # Trừ Mana, chuyển thẻ từ Hand sang Field
        player.mana -= cost
        player.hand.remove(target_card)
        player.field.append(target_card)

        effect_result = self.apply_algorithm_effect(target_card)
        msg = f"Thành công triển khai [{target_card['name']}]. Hiệu ứng: {effect_result}"
        self._log("PLAY_CARD", msg)
        return True, msg

    # --------------------------------------------------------------- effects
    def apply_algorithm_effect(self, card):
        """Áp dụng hiệu ứng theo category và trả về chuỗi mô tả."""
        handlers = {
            "Stack": self._effect_stack,
            "Queue": self._effect_queue,
            "Graph": self._effect_graph,
            "Greedy": self._effect_greedy,
            "DP": self._effect_dp,
        }
        handler = handlers.get(card.get("category"))
        if handler is None:
            return "Hiệu ứng thẻ bài đã được ghi nhận trên bàn đấu."
        return handler()

    def _effect_stack(self):
        self.current_turn_player.shield += 300
        return "Cấu trúc LIFO kích hoạt: Tăng 300 điểm phòng thủ (DEF)."

    def _effect_queue(self):
        card = self.current_turn_player.draw_card()
        if card is None:
            return "Hàng đợi FIFO kích hoạt: Deck đã hết, không rút được thẻ."
        return "Hàng đợi FIFO kích hoạt: Rút thêm 1 thẻ phụ trợ."

    def _effect_graph(self):
        lost = self.opponent_player.take_damage(500)
        self.check_win_condition()
        return f"Duyệt đồ thị (BFS/DFS): Gây 500 sát thương, HP đối thủ mất {lost}."

    def _effect_greedy(self):
        stolen = min(1, self.opponent_player.mana)
        self.opponent_player.mana -= stolen
        self.current_turn_player.gain_mana(stolen)
        return f"Thuật toán tham lam: Đánh cắp {stolen} Mana từ đối thủ."

    def _effect_dp(self):
        self.current_turn_player.gain_mana(1)
        return "Lập trình động (Memoization): Hoàn trả lại 1 Mana chi phí."

    # ------------------------------------------------------------ win check
    def check_win_condition(self):
        p1_dead = self.player1.hp <= 0
        p2_dead = self.player2.hp <= 0
        if p1_dead and p2_dead:
            self.game_over = True
            self.winner = None
            self._log("GAME_OVER", "Cả hai hết HP, trận đấu hòa.")
        elif p1_dead:
            self.game_over = True
            self.winner = self.player2.username
            self._log("GAME_OVER", f"{self.winner} thắng (HP đối thủ về 0).")
        elif p2_dead:
            self.game_over = True
            self.winner = self.player1.username
            self._log("GAME_OVER", f"{self.winner} thắng (HP đối thủ về 0).")

    # ------------------------------------------------------------- snapshot
    def to_dict(self):
        """Ảnh chụp trạng thái trận, dùng cho replay (Task 4) và lưu tiến độ (Task 5)."""
        return {
            "turn": self.turn_count,
            "phase": self.current_phase,
            "current_player": self.current_turn_player.username,
            "game_over": self.game_over,
            "winner": self.winner,
            "player1": self.player1.to_dict(),
            "player2": self.player2.to_dict(),
        }