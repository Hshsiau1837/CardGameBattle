class Player:
    def __init__(self, username, deck):
        self.username = username
        self.hp = 4000
        self.max_mana = 1
        self.mana = 1
        self.deck = list(deck)
        self.hand = []
        self.field = []
        self.graveyard = []

    def draw_card(self):
        if self.deck:
            card = self.deck.pop(0)
            self.hand.append(card)
            return card
        return None

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
        self.winner = None
        
        # Rút 4 lá khởi đầu cho mỗi bên
        for _ in range(4):
            self.player1.draw_card()
            self.player2.draw_card()

    @property
    def current_phase(self):
        return self.PHASES[self.phase_idx]

    def next_phase(self):
        if self.game_over:
            return f"Trận đấu đã kết thúc! Người thắng: {self.winner}"
        
        self.phase_idx += 1
        if self.phase_idx >= len(self.PHASES):
            self.phase_idx = 0
            self.switch_turn()
            
        return f"Chuyển sang {self.current_phase} (Lượt {self.turn_count} - {self.current_turn_player.username})"

    def switch_turn(self):
        self.current_turn_player, self.opponent_player = self.opponent_player, self.current_turn_player
        self.turn_count += 1
        
        # Hồi mana và tăng giới hạn mana (tối đa 10)
        self.current_turn_player.max_mana = min(10, self.current_turn_player.max_mana + 1)
        self.current_turn_player.mana = self.current_turn_player.max_mana
        
        # Rút bài đầu lượt
        drawn = self.current_turn_player.draw_card()
        return drawn

    def play_card(self, card_id):
        if self.game_over:
            return False, "Trận đấu đã kết thúc!"
        if self.current_phase != "MAIN PHASE":
            return False, "Chỉ được đánh thẻ bài trong MAIN PHASE!"
        
        target_card = None
        for c in self.current_turn_player.hand:
            if str(c["id"]) == str(card_id):
                target_card = c
                break
                
        if not target_card:
            return False, "Thẻ bài không có trên tay!"
            
        cost = target_card.get("cost", 0)
        if self.current_turn_player.mana < cost:
            return False, f"Không đủ Mana! Cần {cost} Mana (Hiện có: {self.current_turn_player.mana})."
            
        # Trừ mana và chuyển bài ra sân
        self.current_turn_player.mana -= cost
        self.current_turn_player.hand.remove(target_card)
        self.current_turn_player.field.append(target_card)
        
        # Áp dụng hiệu ứng bài
        effect_msg = self.apply_algorithm_effect(target_card)
        return True, f"Triển khai [{target_card['name']}]. {effect_msg}"

    def apply_algorithm_effect(self, card):
        category = card.get("category", "")
        
        if category == "Stack":
            return "Cấu trúc LIFO: Tăng 300 điểm giáp/phòng thủ."
        elif category == "Queue":
            drawn = self.current_turn_player.draw_card()
            name = drawn['name'] if drawn else 'Hết bài'
            return f"Hàng đợi FIFO: Rút thêm 1 lá ({name})."
        elif category == "Graph":
            self.opponent_player.hp -= 500
            self.check_win_condition()
            return "Duyệt đồ thị (BFS/DFS): Gây 500 sát thương trực tiếp vào LP đối thủ!"
        elif category == "Greedy":
            stolen = min(1, self.opponent_player.mana)
            self.opponent_player.mana -= stolen
            self.current_turn_player.mana += stolen
            return f"Thuật toán tham lam: Đánh cắp {stolen} Mana của đối thủ!"
        elif category == "DP":
            self.current_turn_player.mana += 1
            return "Lập trình động (Memoization): Hoàn lại 1 Mana chi phí."
            
        return "Thẻ bài đã ra sân."

    def check_win_condition(self):
        if self.player1.hp <= 0:
            self.game_over = True
            self.winner = self.player2.username
        elif self.player2.hp <= 0:
            self.game_over = True
            self.winner = self.player1.username