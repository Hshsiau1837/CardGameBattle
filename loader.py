import json
import os
import urllib.request

YGOPRO_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
LOCAL_FILE = "cards.json"
IMAGE_DIR = "card_images"

class CardLoader:
    def __init__(self, filepath=LOCAL_FILE):
        self.filepath = filepath
        self.cards = []

    def load_and_validate(self):
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
            
        # 1. Ưu tiên đọc trực tiếp từ file cards.json cục bộ trước
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.cards = json.load(f)
                print(f"[SUCCESS] Đã nạp thành công {len(self.cards)} thẻ bài từ file local!")
                return self.cards
            except Exception as e:
                print(f"[WARNING] Lỗi đọc file local: {e}")

        # 2. Nếu chưa có file local thì mới gọi API từ web (fallback)
        try:
            print("[INFO] Đang kết nối tới YGOPRODeck API...")
            req = urllib.request.Request(YGOPRO_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                raw_cards = data.get("data", [])
                
                self.cards = []
                for c in raw_cards:
                    card_id = str(c.get("id"))
                    image_url = c["card_images"][0].get("image_url_small", "") if c.get("card_images") else ""
                    
                    card_info = {
                        "id": card_id,
                        "name": c.get("name"),
                        "category": c.get("race", "Normal"),
                        "type": c.get("type", "Monster"),
                        "cost": c.get("level", 4) if c.get("level") else 4,
                        "ATK": c.get("atk", 0),
                        "DEF": c.get("def", 0),
                        "effect": c.get("desc", ""),
                        "image_url": image_url
                    }
                    self.cards.append(card_info)
                
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(self.cards, f, ensure_ascii=False, indent=2)
                    
                print(f"[SUCCESS] Đã nạp thành công {len(self.cards)} thẻ bài từ API!")
                return self.cards

        except Exception as e:
            print(f"[ERROR] Không thể tải dữ liệu thẻ bài: {e}")
            return []