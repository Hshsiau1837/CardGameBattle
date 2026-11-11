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
        
        # Khởi tạo tay bài ban đầu (mỗi người 4 lá)
        for _ in range(4):
            self.player1.draw_card()
            self.player2.draw_card()

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
            
        return f"Chuyển sang phase: {self.current_phase}"

    def switch_turn(self):
        # Đổi lượt chơi
        self.current_turn_player, self.opponent_player = self.opponent_player, self.current_turn_player
        self.turn_count += 1
        
        # Hồi phục và tăng Mana tối đa (giới hạn tối đa 10)
        self.current_turn_player.max_mana = min(10, self.current_turn_player.max_mana + 1)
        self.current_turn_player.mana = self.current_turn_player.max_mana
        
        # Rút bài đầu lượt
        self.current_turn_player.draw_card()

    def play_card(self, card_id):
        if self.current_phase != "MAIN PHASE":
            return False, "Chỉ được triển khai thẻ bài trong MAIN PHASE!"
        
        # Tìm thẻ trên tay
        target_card = None
        for c in self.current_turn_player.hand:
            if c["id"] == card_id:
                target_card = c
                break
                
        if not target_card:
            return False, "Thẻ bài không tồn tại trên tay!"
            
        cost = target_card.get("cost", 0)
        if self.current_turn_player.mana < cost:
            return False, f"Không đủ Mana! Cần {cost} Mana nhưng chỉ còn {self.current_turn_player.mana}."
            
        # Trừ Mana, dịch chuyển thẻ từ Hand sang Field
        self.current_turn_player.mana -= cost
        self.current_turn_player.hand.remove(target_card)
        self.current_turn_player.field.append(target_card)
        
        # Áp dụng hiệu ứng thuật toán
        effect_result = self.apply_algorithm_effect(target_card)
        return True, f"Thành công triển khai [{target_card['name']}]. Hiệu ứng: {effect_result}"

    def apply_algorithm_effect(self, card):
        category = card.get("category")
        if category == "Stack":
            return "Cấu trúc LIFO kích hoạt: Tăng 300 điểm phòng thủ (DEF)."
        elif category == "Queue":
            return "Hàng đợi FIFO kích hoạt: Rút thêm 1 thẻ phụ trợ."
        elif category == "Graph":
            return "Duyệt đồ thị (BFS/DFS): Gây 500 sát thương trực tiếp vào HP đối thủ."
            self.opponent_player.hp -= 500
            self.check_win_condition()
        elif category == "Greedy":
            return "Thuật toán tham lam: Đánh cắp 1 Mana từ đối thủ."
            self.opponent_player.mana = max(0, self.opponent_player.mana - 1)
            self.current_turn_player.mana += 1
        elif category == "DP":
            return "Lập trình động (Memoization): Hoàn trả lại 1 Mana chi phí."
            self.current_turn_player.mana += 1
        return "Hiệu ứng thẻ bài đã được ghi nhận trên bàn đấu."

    def check_win_condition(self):
        if self.player1.hp <= 0:
            self.game_over = True
            self.winner = self.player2.username
        elif self.player2.hp <= 0:
            self.game_over = True
            self.winner = self.player1.username