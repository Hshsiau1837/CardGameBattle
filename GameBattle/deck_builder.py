class DeckBuilder:
    def __init__(self, all_cards):
        self.all_cards = all_cards
        self.user_deck = []
        self.max_deck_size = 30
        self.min_deck_size = 20

    def add_card(self, card):
        # Đếm số lượng thẻ cùng ID trong deck
        count = sum(1 for c in self.user_deck if c["id"] == card["id"])
        if count >= 3:
            return False, "Mỗi thẻ bài chỉ được phép tối đa 3 bản sao trong Deck!"
        
        if len(self.user_deck) >= self.max_deck_size:
            return False, f"Bộ bài đã đạt giới hạn tối đa {self.max_deck_size} lá!"
        
        self.user_deck.append(card)
        return True, "Thêm thẻ thành công."

    def remove_card(self, card_id):
        for c in self.user_deck:
            if c["id"] == card_id:
                self.user_deck.remove(c)
                return True, "Đã loại bỏ thẻ khỏi Deck."
        return False, "Không tìm thấy thẻ trong Deck."

    def validate_deck(self):
        if len(self.user_deck) < self.min_deck_size:
            return False, f"Bộ bài chưa đủ số lượng tối thiểu ({len(self.user_deck)}/{self.min_deck_size} lá)."
        return True, "Bộ bài hợp lệ, sẵn sàng tham chiến!"