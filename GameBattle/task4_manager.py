import json
import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


class DeckRules:
    """Ràng buộc kích thước và số lượng bản sao trong Deck."""
    def __init__(self, min_cards: int = 10, max_cards: int = 30, max_copies: int = 3):
        self.min_cards = min_cards
        self.max_cards = max_cards
        self.max_copies = max_copies

    def can_add_card(self, current_deck: List[Dict[str, Any]], card: Dict[str, Any]) -> Tuple[bool, str]:
        if len(current_deck) >= self.max_cards:
            return False, f"Deck đã đạt giới hạn tối đa {self.max_cards} lá!"
        card_id = str(card.get("id"))
        copies = sum(1 for c in current_deck if str(c.get("id")) == card_id)
        if copies >= self.max_copies:
            return False, f"Chỉ được tối đa {self.max_copies} bản sao cho thẻ '{card.get('name')}'!"
        return True, "OK"

    def is_valid_to_battle(self, current_deck: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if len(current_deck) < self.min_cards:
            return False, f"Cần tối thiểu {self.min_cards} lá để vào trận (hiện có {len(current_deck)})!"
        if len(current_deck) > self.max_cards:
            return False, f"Vượt quá {self.max_cards} lá cho phép!"
        return True, "Deck hợp lệ!"


class TutorialManager:
    """Quản lý các bước hướng dẫn (Tutorial)."""
    STEPS = [
        (
            "Bước 1 - Xây Deck (Deck Building)",
            "Kéo thả hoặc click thẻ từ kho sang Deck bên phải. Chú ý giới hạn kích thước Deck và tối đa 3 bản sao/thẻ."
        ),
        (
            "Bước 2 - Tài nguyên & Nhóm thuật toán",
            "Mỗi lượt bạn có điểm năng lượng (Energy/Cost). Kết hợp Stack, Queue, Graph, Greedy, DP để tối ưu ATK/DEF và hiệu ứng."
        ),
        (
            "Bước 3 - Đấu với Heuristic AI",
            "AI tính điểm heuristic cho từng nước đi (ưu tiên sát thương/cost hiệu quả và thủ vững khi HP thấp). Chọn thẻ trên tay để ra sân/tấn công."
        ),
        (
            "Bước 4 - Replay & Leaderboard",
            "Mọi hành động trong trận đều được lưu lại để xem Replay. Kết quả trận đấu tự động cập nhật lên Leaderboard."
        ),
    ]

    def __init__(self):
        self.active = False
        self.index = 0

    def open(self):
        self.active = True
        self.index = 0

    def close(self):
        self.active = False

    def next_step(self):
        if self.index < len(self.STEPS) - 1:
            self.index += 1
        else:
            self.close()

    def prev_step(self):
        if self.index > 0:
            self.index -= 1

    def current(self) -> Tuple[str, str]:
        return self.STEPS[self.index]


class HeuristicAI:
    """AI đối thủ chọn hành động dựa trên hàm đánh giá Heuristic."""

    CATEGORY_BONUS = {
        "Greedy": 1.25,
        "DP": 1.20,
        "Graph": 1.15,
        "Stack": 1.10,
        "Queue": 1.10,
    }

    def score_card(self, card: Dict[str, Any], ai_energy: int, ai_hp: int, player_hp: int) -> float:
        cost = max(1, int(card.get("cost", 1)))
        if cost > ai_energy:
            return -1.0

        atk = int(card.get("ATK", 0))
        def_val = int(card.get("DEF", 0))
        category = str(card.get("category", ""))
        cat_weight = self.CATEGORY_BONUS.get(category, 1.0)

        # Heuristic: cân bằng giữa hiệu suất tấn công/chi phí, phòng thủ khi máu thấp, và dứt điểm khi đối thủ ít máu
        offense_ratio = (atk / cost) * 1.4
        defense_factor = (def_val / max(1, cost)) * (1.6 if ai_hp < 4000 else 0.7)
        finisher_bonus = 250.0 if (atk >= player_hp and atk > 0) else 0.0

        return (offense_ratio + defense_factor) * cat_weight + finisher_bonus

    def choose_action(
        self,
        ai_hand: List[Dict[str, Any]],
        ai_field: List[Dict[str, Any]],
        player_field: List[Dict[str, Any]],
        ai_energy: int,
        ai_hp: int,
        player_hp: int,
    ) -> Dict[str, Any]:
        best_card = None
        best_score = -1.0

        for card in ai_hand:
            s = self.score_card(card, ai_energy, ai_hp, player_hp)
            if s > best_score:
                best_score = s
                best_card = card

        # Nếu có thẻ trên sân và chưa có thẻ phù hợp để ra thêm, ưu tiên tấn công bằng thẻ ATK cao nhất
        if ai_field:
            strongest_attacker = max(ai_field, key=lambda c: int(c.get("ATK", 0)))
            if int(strongest_attacker.get("ATK", 0)) > 0 and (best_card is None or best_score < 220):
                target = None
                if player_field:
                    # Heuristic diệt quái thủ/công thấp nhất trước để mở đường
                    target = min(player_field, key=lambda c: min(int(c.get("ATK", 999999)), int(c.get("DEF", 999999))))
                return {
                    "type": "attack",
                    "attacker": strongest_attacker,
                    "target": target,
                    "score": round(best_score, 2),
                }

        if best_card is not None:
            return {
                "type": "summon",
                "card": best_card,
                "score": round(best_score, 2),
            }

        return {"type": "end_turn", "score": 0.0}


class ReplayRecorder:
    """Ghi và đọc chuỗi hành động trận đấu để phát lại (Replay)."""

    def __init__(self, replay_path: str = "last_replay.json"):
        self.replay_path = replay_path
        self.actions: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {}

    def start_match(self, player_deck_names: List[str], ai_deck_names: List[str]):
        self.actions = []
        self.meta = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "player_deck": player_deck_names,
            "ai_deck": ai_deck_names,
            "result": "IN_PROGRESS",
        }

    def record(self, turn: int, actor: str, action_type: str, detail: str, player_hp: int, ai_hp: int):
        self.actions.append({
            "step": len(self.actions) + 1,
            "turn": turn,
            "actor": actor,
            "action_type": action_type,
            "detail": detail,
            "player_hp": player_hp,
            "ai_hp": ai_hp,
        })

    def finish_and_save(self, result: str):
        self.meta["result"] = result
        payload = {"meta": self.meta, "actions": self.actions}
        with open(self.replay_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load_replay(self) -> Dict[str, Any]:
        if not os.path.exists(self.replay_path):
            return {"meta": {}, "actions": []}
        with open(self.replay_path, "r", encoding="utf-8") as f:
            return json.load(f)


class LeaderboardManager:
    """Lưu và xếp hạng thành tích người chơi."""

    def __init__(self, file_path: str = "leaderboard.json"):
        self.file_path = file_path
        self.entries: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return [
                {"player": "Bot_Heuristic", "wins": 2, "losses": 0, "points": 200},
                {"player": "Player_1", "wins": 1, "losses": 1, "points": 110},
            ]
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def record_result(self, player_name: str, won: bool, remaining_hp: int):
        entry = next((e for e in self.entries if e.get("player") == player_name), None)
        if not entry:
            entry = {"player": player_name, "wins": 0, "losses": 0, "points": 0}
            self.entries.append(entry)

        if won:
            entry["wins"] += 1
            entry["points"] += 100 + max(0, remaining_hp // 100)
        else:
            entry["losses"] += 1
            entry["points"] += 20

        self.entries.sort(key=lambda x: (-x.get("points", 0), -x.get("wins", 0)))
        self.save()

    def top(self, limit: int = 6) -> List[Dict[str, Any]]:
        return self.entries[:limit]


def summarize_deck(deck: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Thống kê nhanh số lượng, chi phí trung bình và nhóm thuật toán."""
    count = len(deck)
    avg_cost = round(sum(int(c.get("cost", 0)) for c in deck) / count, 2) if count else 0.0
    cats = Counter(str(c.get("category", "Other")) for c in deck)
    return {"count": count, "avg_cost": avg_cost, "categories": dict(cats)}