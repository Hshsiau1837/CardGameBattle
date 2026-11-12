from task3_engine.engine import GameEngine

def run_simulation():
    deck_p1 = [
        {"id": "STK-01", "name": "Stack Push", "category": "Stack", "cost": 1},
        {"id": "GRA-01", "name": "BFS Traversal", "category": "Graph", "cost": 2},
        {"id": "QUE-01", "name": "Queue Enqueue", "category": "Queue", "cost": 1},
    ]
    deck_p2 = [
        {"id": "DP-01", "name": "Memoization Cache", "category": "DP", "cost": 1},
        {"id": "GRE-01", "name": "Activity Selector", "category": "Greedy", "cost": 2},
    ]

    engine = GameEngine("Alice (StackMaster)", deck_p1, "Bob (AlgoKnight)", deck_p2)

    print("=" * 60)
    print(" BẮT ĐẦU MÔ PHỎNG TRẬN ĐẤU ALGORITHMIC CARD BATTLE ")
    print("=" * 60)

    # Mô phỏng 3 lượt đấu đầu tiên
    for turn in range(1, 4):
        print(f"\n--- LƯỢT THỨ {turn} | Người chơi: {engine.current_turn_player.username} ---")
        print(f"Trạng thái: HP = {engine.current_turn_player.hp} | Mana = {engine.current_turn_player.mana}/{engine.current_turn_player.max_mana}")
        
        # Duyệt qua các pha
        for _ in range(5):
            phase_msg = engine.next_phase()
            print(f"  -> {phase_msg}")
            
            # Nếu đến Main Phase, thử đánh thẻ đầu tiên trên tay nếu đủ Mana
            if engine.current_phase == "MAIN PHASE" and engine.current_turn_player.hand:
                card_to_play = engine.current_turn_player.hand[0]
                success, log_msg = engine.play_card(card_to_play["id"])
                print(f"     [HÀNH ĐỘNG] Chơi thẻ '{card_to_play['name']}' (Cost: {card_to_play['cost']}) -> Kết quả: {log_msg}")

        print(f"Kết thúc lượt {turn}. HP Đối thủ ({engine.opponent_player.username}): {engine.opponent_player.hp}")
        
        if engine.game_over:
            print(f"\n[CHIẾN THẮNG] Người chiến thắng là: {engine.winner}!")
            break

    print("=" * 60)
    print(" HOÀN TẤT MÔ PHỎNG KỊCH BẢN TRẬN ĐẤU ")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation()