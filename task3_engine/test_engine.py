import unittest
from task3_engine.engine import GameEngine, MAX_MANA_CAP


def make_card(card_id, category, cost, name=None):
    return {"id": card_id, "name": name or card_id, "category": category, "cost": cost}


def make_deck(size=10):
    cats = ["Stack", "Graph", "DP", "Queue", "Greedy"]
    return [make_card(f"C-{i:02d}", cats[i % 5], 1 + i % 3) for i in range(size)]


class TestAlgoCardEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine("Player1", make_deck(), "Player2", make_deck())

    def go_main(self, hand=None, mana=None):
        """Đưa trận sang MAIN PHASE của P1, tùy chọn gán tay bài và mana."""
        self.engine.phase_idx = 2
        if hand is not None:
            self.engine.player1.hand = hand
        if mana is not None:
            self.engine.player1.mana = mana

    # ---------------------------------------------------------- khởi tạo, phase
    def test_initial_state(self):
        p1 = self.engine.player1
        self.assertEqual(p1.hp, 4000)
        self.assertEqual(len(p1.hand), 4)
        self.assertEqual(len(p1.deck), 6)
        self.assertEqual(self.engine.current_turn_player.username, "Player1")
        self.assertEqual(self.engine.current_phase, "DRAW PHASE")

    def test_small_deck_draws_what_it_has(self):
        e = GameEngine("A", make_deck(3), "B", make_deck(3))
        self.assertEqual(len(e.player1.hand), 3)

    def test_phase_transitions(self):
        self.engine.next_phase()
        self.assertEqual(self.engine.current_phase, "STANDBY PHASE")
        self.engine.next_phase()
        self.assertEqual(self.engine.current_phase, "MAIN PHASE")

    def test_full_cycle_switches_turn(self):
        for _ in range(5):
            self.engine.next_phase()
        e = self.engine
        self.assertEqual(e.current_phase, "DRAW PHASE")
        self.assertEqual(e.current_turn_player.username, "Player2")
        self.assertEqual(e.turn_count, 2)
        self.assertEqual(e.player2.max_mana, 2)
        self.assertEqual(e.player2.mana, 2)
        self.assertEqual(len(e.player2.hand), 5)  # rút thêm 1 đầu lượt

    def test_mana_capped_at_10(self):
        self.engine.player2.max_mana = 10
        for _ in range(5):
            self.engine.next_phase()
        self.assertEqual(self.engine.player2.max_mana, MAX_MANA_CAP)

    # ------------------------------------------------------------- play_card
    def test_play_card_cost_validation(self):
        self.go_main(hand=[make_card("DP-01", "DP", 2)], mana=1)
        success, msg = self.engine.play_card("DP-01")
        self.assertFalse(success)
        self.assertIn("Không đủ Mana", msg)

        self.go_main(hand=[make_card("STK-01", "Stack", 1)], mana=1)
        success, msg = self.engine.play_card("STK-01")
        self.assertTrue(success)
        self.assertEqual(self.engine.player1.mana, 0)
        self.assertEqual(len(self.engine.player1.field), 1)
        self.assertEqual(len(self.engine.player1.hand), 0)

    def test_play_card_wrong_phase(self):
        self.engine.player1.hand = [make_card("STK-01", "Stack", 1)]
        success, msg = self.engine.play_card("STK-01")
        self.assertFalse(success)
        self.assertIn("MAIN PHASE", msg)

    def test_play_card_not_in_hand(self):
        self.go_main(hand=[])
        success, msg = self.engine.play_card("XXX")
        self.assertFalse(success)
        self.assertIn("không tồn tại", msg)

    # --------------------------------------------------------------- hiệu ứng
    def test_stack_adds_shield_and_absorbs_damage(self):
        self.go_main(hand=[make_card("STK-01", "Stack", 1)], mana=1)
        self.engine.play_card("STK-01")
        p1 = self.engine.player1
        self.assertEqual(p1.shield, 300)
        lost = p1.take_damage(500)
        self.assertEqual(lost, 200)
        self.assertEqual(p1.shield, 0)
        self.assertEqual(p1.hp, 3800)

    def test_graph_deals_500_damage(self):
        self.go_main(hand=[make_card("GRA-01", "Graph", 1)], mana=1)
        self.engine.play_card("GRA-01")
        self.assertEqual(self.engine.player2.hp, 3500)

    def test_graph_damage_blocked_by_shield(self):
        self.engine.player2.shield = 300
        self.go_main(hand=[make_card("GRA-01", "Graph", 1)], mana=1)
        self.engine.play_card("GRA-01")
        self.assertEqual(self.engine.player2.shield, 0)
        self.assertEqual(self.engine.player2.hp, 3800)

    def test_queue_draws_extra_card(self):
        self.go_main(hand=[make_card("QUE-01", "Queue", 1)], mana=1)
        deck_before = len(self.engine.player1.deck)
        self.engine.play_card("QUE-01")
        self.assertEqual(len(self.engine.player1.hand), 1)
        self.assertEqual(len(self.engine.player1.deck), deck_before - 1)

    def test_greedy_steals_mana(self):
        self.engine.player2.mana = 3
        self.go_main(hand=[make_card("GRE-01", "Greedy", 1)], mana=2)
        self.engine.play_card("GRE-01")
        self.assertEqual(self.engine.player2.mana, 2)
        self.assertEqual(self.engine.player1.mana, 2)  # 2 - 1 (cost) + 1 (cướp)

    def test_greedy_steals_nothing_if_opponent_has_no_mana(self):
        self.engine.player2.mana = 0
        self.go_main(hand=[make_card("GRE-01", "Greedy", 1)], mana=2)
        self.engine.play_card("GRE-01")
        self.assertEqual(self.engine.player1.mana, 1)

    def test_dp_refunds_mana(self):
        self.go_main(hand=[make_card("DP-01", "DP", 1)], mana=1)
        self.engine.play_card("DP-01")
        self.assertEqual(self.engine.player1.mana, 1)  # 1 - 1 + 1

    def test_unknown_category_has_no_side_effect(self):
        self.go_main(hand=[make_card("N-01", "Normal", 1)], mana=1)
        success, _ = self.engine.play_card("N-01")
        self.assertTrue(success)
        self.assertEqual(self.engine.player2.hp, 4000)

    # ------------------------------------------------------------- điều kiện thắng
    def test_win_by_hp(self):
        self.engine.player2.hp = 500
        self.go_main(hand=[make_card("GRA-01", "Graph", 1)], mana=1)
        self.engine.play_card("GRA-01")
        self.assertTrue(self.engine.game_over)
        self.assertEqual(self.engine.winner, "Player1")
        self.assertEqual(self.engine.player2.hp, 0)

    def test_no_actions_after_game_over(self):
        self.engine.player2.hp = 500
        self.go_main(hand=[make_card("GRA-01", "Graph", 1), make_card("STK-01", "Stack", 1)], mana=2)
        self.engine.play_card("GRA-01")
        success, msg = self.engine.play_card("STK-01")
        self.assertFalse(success)
        self.assertIn("kết thúc", msg)
        self.assertIn("kết thúc", self.engine.next_phase())

    def test_lose_when_deck_empty_on_draw(self):
        self.engine.player2.deck = []
        for _ in range(5):
            self.engine.next_phase()
        self.assertTrue(self.engine.game_over)
        self.assertEqual(self.engine.winner, "Player1")

    # ------------------------------------------------------------ log, snapshot
    def test_log_records_actions(self):
        self.go_main(hand=[make_card("STK-01", "Stack", 1)], mana=1)
        self.engine.play_card("STK-01")
        last = self.engine.log[-1]
        self.assertEqual(last["action_type"], "PLAY_CARD")
        self.assertEqual(last["player"], "Player1")
        self.assertEqual(last["turn"], 1)

    def test_game_over_logged_after_play_card(self):
        self.engine.player2.hp = 500
        self.go_main(hand=[make_card("GRA-01", "Graph", 1)], mana=1)
        self.engine.play_card("GRA-01")
        self.assertEqual(self.engine.log[-2]["action_type"], "PLAY_CARD")
        self.assertEqual(self.engine.log[-1]["action_type"], "GAME_OVER")

    def test_to_dict_snapshot(self):
        snap = self.engine.to_dict()
        self.assertEqual(snap["turn"], 1)
        self.assertEqual(snap["player1"]["hp"], 4000)
        self.assertEqual(len(snap["player1"]["hand"]), 4)
        self.assertFalse(snap["game_over"])


if __name__ == "__main__":
    unittest.main()
