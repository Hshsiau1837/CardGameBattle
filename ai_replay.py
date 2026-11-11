import json

class ReplayRecorder:
    def __init__(self):
        self.actions = []

    def log(self, turn, phase, player, action_type, details):
        self.actions.append({
            "turn": turn,
            "phase": phase,
            "player": player,
            "action_type": action_type,
            "details": details
        })

    def export_json(self):
        return json.dumps(self.actions, ensure_ascii=False, indent=2)

class HeuristicAI:
    def __init__(self, name, deck):
        self.username = name
        self.deck = list(deck)
        self.hp = 4000
        self.max_mana = 1
        self.mana = 1
        self.hand = []
        self.field = []

    def decide_move(self):
        """
        Chiến thuật Heuristic đơn giản:
        - Lọc các thẻ trên tay có cost <= mana hiện tại.
        - Ưu tiên chọn thẻ có cost cao nhất có thể chi trả để tối ưu sức mạnh.
        """
        playable_cards = [c for c in self.hand if c.get("cost", 0) <= self.mana]
        if not playable_cards:
            return None
        
        # Chọn thẻ có cost cao nhất để đánh
        best_card = max(playable_cards, key=lambda x: x.get("cost", 0))
        return best_card