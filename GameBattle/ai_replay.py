import json
import os
from typing import Any, Dict, List, Optional


class ReplayRecorder:
    def __init__(self, filepath: str = "last_replay.json", auto_save: bool = True):
        self.filepath = filepath
        self.auto_save = auto_save
        self.actions: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {}

    def start_match(self, player_deck_names: List[str], ai_deck_names: List[str]):
        self.actions = []
        self.meta = {
            "player_deck": player_deck_names,
            "ai_deck": ai_deck_names,
            "result": "IN_PROGRESS",
        }
        if self.auto_save:
            self._write_payload()

    def log(self, turn: int, phase: str, player: str, action_type: str, details: Any):
        self.actions.append({
            "step": len(self.actions) + 1,
            "turn": turn,
            "phase": phase,
            "player": player,
            "action_type": action_type,
            "details": details,
        })
        if self.auto_save:
            self._write_payload()

    def export_json(self) -> str:
        return json.dumps(self.actions, ensure_ascii=False, indent=2)

    def _write_payload(self):
        payload = {
            "meta": self.meta,
            "actions": self.actions,
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def save_file(self, result: str, player_hp: int, ai_hp: int) -> str:
        self.meta["result"] = result
        self.meta["player_hp"] = player_hp
        self.meta["ai_hp"] = ai_hp
        self._write_payload()
        return self.filepath

    def load_file(self) -> Dict[str, Any]:
        # Nếu đang có actions trong RAM và file chưa có hoặc ít hơn, ưu tiên dữ liệu mới nhất
        file_data: Dict[str, Any] = {"meta": {}, "actions": []}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    file_data = {
                        "meta": raw.get("meta", {}) if isinstance(raw.get("meta"), dict) else {},
                        "actions": raw.get("actions", []) if isinstance(raw.get("actions"), list) else [],
                    }
                elif isinstance(raw, list):
                    file_data = {"meta": {}, "actions": raw}
            except Exception:
                file_data = {"meta": {}, "actions": []}

        if len(self.actions) > len(file_data["actions"]):
            return {
                "meta": dict(self.meta),
                "actions": list(self.actions),
            }
        return file_data
    from typing import Any, Dict, List, Optional


class HeuristicAI:
    def __init__(self, name: str = "Heuristic AI", deck: Optional[List[Dict[str, Any]]] = None):
        self.username = name
        self.deck: List[Dict[str, Any]] = [dict(c) for c in (deck or [])]
        self.hp: int = 8000
        self.max_mana: int = 10
        self.mana: int = 10
        self.hand: List[Dict[str, Any]] = []
        self.field: List[Dict[str, Any]] = []

    def start_turn(self, turn: int):
        """Bắt đầu lượt: +2 vào mana hiện tại và reset trạng thái tấn công."""
        if turn > 1:
            self.mana += 2
        self.max_mana = max(self.max_mana, self.mana)
        for unit in self.field:
            unit["_attacked"] = False

    def decide_move(self) -> Optional[Dict[str, Any]]:
        """Lọc thẻ trên tay có cost <= mana hiện tại, ưu tiên cost cao nhất rồi ATK cao nhất."""
        playable_cards = [c for c in self.hand if int(c.get("cost", 0)) <= self.mana]
        if not playable_cards:
            return None
        return max(
            playable_cards,
            key=lambda x: (int(x.get("cost", 0)), int(x.get("ATK", 0))),
        )

    def pick_attacker(self) -> Optional[Dict[str, Any]]:
        """Chọn quái chưa tấn công có ATK > 0 trên sân AI."""
        ready = [u for u in self.field if not u.get("_attacked") and int(u.get("ATK", 0)) > 0]
        if not ready:
            return None
        return max(ready, key=lambda u: int(u.get("ATK", 0)))