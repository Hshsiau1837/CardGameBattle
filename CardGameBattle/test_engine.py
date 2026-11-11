import unittest
from engine import GameEngine, Player

class TestAlgoCardEngine(unittest.TestCase):
    def setUp(self):
        self.sample_deck = [
            {"id": "STK-01", "name": "Stack Push", "category": "Stack", "cost": 1},
            {"id": "GRA-01", "name": "BFS Traversal", "category": "Graph", "cost": 3},
            {"id": "DP-01", "name": "Memoization", "category": "DP", "cost": 2}
        ]
        self.engine = GameEngine("Player1", self.sample_deck, "Player2", self.sample_deck)

    def test_initial_state(self):
        self.assertEqual(self.engine.player1.hp, 4000)
        self.assertEqual(len(self.engine.player1.hand), 4)
        self.assertEqual(self.engine.current_turn_player.username, "Player1")
        self.assertEqual(self.engine.current_phase, "DRAW PHASE")

    def test_phase_transitions(self):
        self.engine.next_phase() # Sang Standby
        self.assertEqual(self.engine.current_phase, "STANDBY PHASE")
        self.engine.next_phase() # Sang Main Phase
        self.assertEqual(self.engine.current_phase, "MAIN PHASE")

    def test_play_card_cost_validation(self):
        # Đưa game sang Main Phase
        self.engine.phase_idx = 2 
        
        # P1 có sẵn 1 Mana ở lượt đầu, thử đánh thẻ cost = 2 (DP-01) -> Phải thất bại
        self.engine.player1.hand = [{"id": "DP-01", "name": "Memoization", "category": "DP", "cost": 2}]
        success, msg = self.engine.play_card("DP-01")
        self.assertFalse(success)
        self.assertIn("Không đủ Mana", msg)

        # Thử đánh thẻ cost = 1 (STK-01) -> Phải thành công
        self.engine.player1.hand = [{"id": "STK-01", "name": "Stack Push", "category": "Stack", "cost": 1}]
        self.engine.player1.mana = 1
        success, msg = self.engine.play_card("STK-01")
        self.assertTrue(success)
        self.assertEqual(self.engine.player1.mana, 0)
        self.assertEqual(len(self.engine.player1.field), 1)

if __name__ == "__main__":
    unittest.main()