import json
import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen

import pygame


def load_vietnamese_font(size: int, bold: bool = False) -> pygame.font.Font:
    candidates = (
        [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\tahomabd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return pygame.font.SysFont("arial", size, bold=bold)


def load_cards_data(json_path: str = "cards.json") -> List[Dict[str, Any]]:
    candidates = [json_path, "card.json"] if json_path == "cards.json" else [json_path]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list) and raw:
                cleaned = []
                for idx, c in enumerate(raw):
                    if not isinstance(c, dict):
                        continue
                    cid = str(c.get("id", idx + 1))
                    effect = " ".join(str(c.get("effect", "")).replace("●", "-").split())
                    cleaned.append({
                        "id": cid,
                        "name": str(c.get("name", f"Card #{cid}")),
                        "category": str(c.get("category", "Greedy")),
                        "type": str(c.get("type", "Effect Monster")),
                        "cost": max(1, int(c.get("cost", 2) or 2)),
                        "ATK": int(c.get("ATK", 0) or 0),
                        "DEF": int(c.get("DEF", 0) or 0),
                        "effect": effect,
                        "image_url": str(c.get("image_url", "")),
                    })
                if cleaned:
                    return cleaned
        except Exception:
            continue
    return []


class ImageCache:
    def __init__(self, local_dir: str = "card_images"):
        self.local_dir = local_dir
        self.cache: Dict[str, Optional[pygame.Surface]] = {}

    def get(self, card: Dict[str, Any], size: Tuple[int, int]) -> Optional[pygame.Surface]:
        cid = str(card.get("id", ""))
        key = f"{cid}_{size[0]}x{size[1]}"
        if key in self.cache:
            return self.cache[key]

        surf: Optional[pygame.Surface] = None
        local_path = os.path.join(self.local_dir, f"{cid}.jpg")
        if os.path.exists(local_path):
            try:
                img = pygame.image.load(local_path).convert()
                surf = pygame.transform.smoothscale(img, size)
            except Exception:
                surf = None

        if surf is None and card.get("image_url"):
            try:
                with urlopen(card["image_url"], timeout=2.0) as resp:
                    data = resp.read()
                img = pygame.image.load(BytesIO(data), "jpg").convert()
                surf = pygame.transform.smoothscale(img, size)
            except Exception:
                surf = None

        self.cache[key] = surf
        return surf


class Button:
    def __init__(self, rect: Tuple[int, int, int, int], label: str, bg=(45, 58, 82), fg=(240, 244, 248)):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.bg = bg
        self.fg = fg

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, active: bool = False):
        color = (78, 125, 200) if active else self.bg
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, (130, 155, 195), self.rect, width=2, border_radius=6)
        txt = font.render(self.label, True, self.fg)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def clicked(self, pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class HorizontalSlider:
    def __init__(self, track_rect: Tuple[int, int, int, int]):
        self.track = pygame.Rect(track_rect)
        self.thumb = pygame.Rect(track_rect)
        self.dragging = False
        self.drag_offset = 0

    def update_thumb(self, scroll: int, max_scroll: int, total_items: int, step: int = 165):
        if max_scroll > 0 and total_items > 0:
            thumb_w = max(60, int(self.track.width * (self.track.width / (total_items * step))))
            thumb_w = min(thumb_w, self.track.width)
            track_w = max(1, self.track.width - thumb_w)
            thumb_x = self.track.x + int((scroll / max_scroll) * track_w)
            self.thumb = pygame.Rect(thumb_x, self.track.y, thumb_w, self.track.height)
        else:
            self.thumb = pygame.Rect(self.track.x, self.track.y, self.track.width, self.track.height)

    def handle_mouse_down(self, pos: Tuple[int, int], max_scroll: int) -> Optional[int]:
        if self.thumb.collidepoint(pos):
            self.dragging = True
            self.drag_offset = pos[0] - self.thumb.x
            return None
        if self.track.collidepoint(pos) and max_scroll > 0:
            track_w = max(1, self.track.width - self.thumb.width)
            ratio = (pos[0] - self.track.x - self.thumb.width / 2) / track_w
            return int(max(0, min(1, ratio)) * max_scroll)
        return None

    def handle_mouse_move(self, mouse_x: int, max_scroll: int) -> Optional[int]:
        if not self.dragging:
            return None
        track_w = max(1, self.track.width - self.thumb.width)
        new_x = max(self.track.x, min(self.track.right - self.thumb.width, mouse_x - self.drag_offset))
        return int(((new_x - self.track.x) / track_w) * max_scroll)

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, (32, 42, 58), self.track, border_radius=8)
        pygame.draw.rect(screen, (85, 110, 145), self.track, width=1, border_radius=8)
        pygame.draw.rect(screen, (95, 150, 225), self.thumb, border_radius=8)


def draw_wrapped_text(
    screen: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    x: int,
    y: int,
    max_w: int,
    max_y: int,
) -> int:
    words = text.split(" ")
    line = ""
    line_h = font.get_linesize() + 2
    cur_y = y
    for w in words:
        test = f"{line} {w}".strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            if cur_y + line_h > max_y:
                return cur_y
            screen.blit(font.render(line, True, color), (x, cur_y))
            cur_y += line_h
            line = w
    if line and cur_y + line_h <= max_y:
        screen.blit(font.render(line, True, color), (x, cur_y))
        cur_y += line_h
    return cur_y