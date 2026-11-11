# Mẫu logic tiêu chuẩn cho Task 3 trong engine.py

class GameEngine:
    def __init__(self, player1_deck, player2_deck):
        self.player1 = {"name": "Player1", "hp": 40, "mana": 1, "max_mana": 1, "hand": [], "deck": player1_deck, "discard": []}
        self.player2 = {"name": "Player2", "hp": 40, "mana": 1, "max_mana": 1, "hand": [], "deck": player2_deck, "discard": []}
        self.turn = 1
        self.current_player = self.player1
        self.opponent = self.player2
        self.game_over = False
        self.winner = None
        self.action_logs = []

    def start_turn(self):
        # Tăng max mana theo lượt (tối đa 10)
        self.current_player["max_mana"] = min(10, self.turn)
        self.current_player["mana"] = self.current_player["max_mana"]
        
        # Rút 1 lá bài đầu lượt
        if self.current_player["deck"]:
            card = self.current_player["deck"].pop(0)
            self.current_player["hand"].append(card)
            
        self.log_action(f"Bắt đầu lượt {self.turn} của {self.current_player['name']}. Mana: {self.current_player['mana']}")

    def play_card(self, card_index):
        if self.game_over:
            return False, "Trận đấu đã kết thúc!"
            
        if card_index < 0 or card_index >= len(self.current_player["hand"]):
            return False, "Vị trí lá bài không hợp lệ!"

        card = self.current_player["hand"][card_index]

        # 1. Kiểm tra Cost (Kiểm tra điều kiện dùng bài)
        if self.current_player["mana"] < card.cost:
            self.log_action(f"Thất bại: {self.current_player['name']} không đủ Mana dùng [{card.name}] (Cần {card.cost}, có {self.current_player['mana']})")
            return False, "Không đủ Mana!"

        # 2. Trừ Mana & Bỏ bài vào mộ
        self.current_player["mana"] -= card.cost
        self.current_player["hand"].pop(card_index)
        self.current_player["discard"].append(card)

        # 3. Áp dụng hiệu ứng bài (Effect Engine)
        self.apply_card_effect(card)
        self.log_action(f"{self.current_player['name']} sử dụng [{card.name}]")

        # 4. Kiểm tra điều kiện thắng
        self.check_win_condition()
        return True, "Thành công"

    def apply_card_effect(self, card):
        # Ví dụ xử lý hiệu ứng cơ bản
        if hasattr(card, 'damage') and card.damage > 0:
            self.opponent["hp"] -= card.damage
            self.log_action(f"-> Gây {card.damage} sát thương lên {self.opponent['name']} (HP còn: {self.opponent['hp']})")
        if hasattr(card, 'heal') and card.heal > 0:
            self.current_player["hp"] += card.heal
            self.log_action(f"-> Hồi {card.heal} HP cho {self.current_player['name']} (HP hiện tại: {self.current_player['hp']})")

    def end_turn(self):
        self.log_action(f"{self.current_player['name']} kết thúc lượt.")
        self.current_player, self.opponent = self.opponent, self.current_player
        if self.current_player == self.player1:
            self.turn += 1
        self.start_turn()

    def check_win_condition(self):
        if self.opponent["hp"] <= 0:
            self.game_over = True
            self.winner = self.current_player["name"]
            self.log_action(f"🏆 TRẬN ĐẤU KẾT THÚC! Người thắng: {self.winner}")

    def log_action(self, message):
        print(message)
        self.action_logs.append({"turn": self.turn, "player": self.current_player["name"], "log": message})