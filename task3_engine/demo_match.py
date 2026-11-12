"""Demo Task 3: chạy kịch bản trận mẫu và in log từng lượt."""
from task3_engine.engine import GameEngine


def card(card_id, name, category, cost):
    return {"id": card_id, "name": name, "category": category, "cost": cost}


def build_deck(prefix):
    return [
        card(f"{prefix}-STK", "Stack Push", "Stack", 1),
        card(f"{prefix}-GRA", "BFS Traversal", "Graph", 2),
        card(f"{prefix}-QUE", "Queue Enqueue", "Queue", 1),
        card(f"{prefix}-DP", "Memoization Cache", "DP", 1),
        card(f"{prefix}-GRE", "Activity Selector", "Greedy", 2),
        card(f"{prefix}-GRA2", "DFS Traversal", "Graph", 3),
        card(f"{prefix}-STK2", "Stack Pop", "Stack", 2),
        card(f"{prefix}-DP2", "Knapsack Table", "DP", 3),
        card(f"{prefix}-QUE2", "Queue Dequeue", "Queue", 1),
        card(f"{prefix}-GRE2", "Coin Change Greedy", "Greedy", 1),
        card(f"{prefix}-GRA3", "Dijkstra", "Graph", 4),
        card(f"{prefix}-STK3", "Stack Overflow Guard", "Stack", 3),
    ]


def play_turn(engine):
    """Đi hết 1 lượt: ở MAIN PHASE đánh thẻ có cost cao nhất chi trả được cho đến khi hết Mana."""
    player = engine.current_turn_player
    print(f"\n--- LƯỢT {engine.turn_count} | {player.username} | "
          f"HP {player.hp} | DEF {player.shield} | Mana {player.mana}/{player.max_mana} ---")
    for _ in range(len(engine.PHASES)):
        if engine.game_over:
            return
        msg = engine.next_phase()
        print(f"  -> {msg}")
        if engine.current_phase == "MAIN PHASE" and not engine.game_over:
            while True:
                me = engine.current_turn_player
                playable = [c for c in me.hand if c["cost"] <= me.mana]
                if not playable:
                    break
                best = max(playable, key=lambda c: c["cost"])
                ok, log_msg = engine.play_card(best["id"])
                print(f"     [ĐÁNH THẺ] {best['name']} (cost {best['cost']}) -> {log_msg}")
                if engine.game_over:
                    return


def run_scenario(title, engine, max_turns):
    print("=" * 64)
    print(f" {title}")
    print("=" * 64)
    # Ở lượt đầu tiên, engine đang ở DRAW PHASE của P1 nên cho đi tiếp từ STANDBY
    played = 0
    while played < max_turns and not engine.game_over:
        play_turn(engine)
        played += 1
    p1, p2 = engine.player1, engine.player2
    print("\n" + "-" * 64)
    print(f"KẾT QUẢ: {p1.username} HP {p1.hp} | {p2.username} HP {p2.hp}")
    if engine.game_over:
        print(f"[CHIẾN THẮNG] {engine.winner or 'Hòa'}")
    else:
        print("Trận chưa kết thúc sau số lượt mô phỏng.")
    print(f"Tổng số dòng log: {len(engine.log)}\n")


def main():
    # Kịch bản 1: đấu bình thường 6 lượt
    e1 = GameEngine("Alice (StackMaster)", build_deck("A"), "Bob (AlgoKnight)", build_deck("B"))
    run_scenario("KỊCH BẢN 1: 6 LƯỢT ĐẤU ĐẦU TIÊN", e1, max_turns=6)

    # Kịch bản 2: đối thủ còn ít HP để minh họa điều kiện thắng
    e2 = GameEngine("Alice (StackMaster)", build_deck("A"), "Bob (AlgoKnight)", build_deck("B"))
    e2.player2.hp = 800
    run_scenario("KỊCH BẢN 2: ĐIỀU KIỆN THẮNG (HP Bob = 800)", e2, max_turns=10)

    print("Log JSON lượt cuối kịch bản 2 (5 dòng):")
    for entry in e2.log[-5:]:
        print(" ", entry)


if __name__ == "__main__":
    main()
