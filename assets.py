import os
import struct
import zlib
import tkinter as tk
import customtkinter as ctk

def load_ctk_logo_image(path, size):
    try:
        from PIL import Image
        pil_image = Image.open(path)
        return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(size, size))
    except Exception:
        return None

def point_in_polygon(x, y, points):
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside

def hex_to_rgba(hex_color, alpha=255):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)

def render_logo_rgba(size):
    transparent = (0, 0, 0, 0)
    pixels = [bytearray([0, 0, 0, 0] * size) for _ in range(size)]
    polygons = [
        ("#58B7FF", [(0.21, 0.07), (0.50, 0.07), (0.37, 0.28)]),
        ("#3496F7", [(0.21, 0.07), (0.37, 0.28), (0.21, 0.36)]),
        ("#145FCC", [(0.21, 0.36), (0.37, 0.28), (0.37, 0.47), (0.21, 0.44)]),
        ("#1F74E6", [(0.37, 0.28), (0.50, 0.07), (0.50, 0.30)]),
        ("#318EEE", [(0.50, 0.07), (0.86, 0.28), (0.68, 0.40), (0.50, 0.30)]),
        ("#0C56C1", [(0.21, 0.44), (0.37, 0.47), (0.28, 0.57), (0.21, 0.54)]),
        ("#4FB3FF", [(0.16, 0.73), (0.36, 0.60), (0.50, 0.70), (0.50, 0.92)]),
        ("#1C78E1", [(0.50, 0.60), (0.66, 0.56), (0.66, 0.82), (0.50, 0.70)]),
        ("#0A5BC8", [(0.50, 0.70), (0.66, 0.82), (0.50, 0.92)]),
        ("#5EC0FF", [(0.50, 0.43), (0.68, 0.40), (0.66, 0.56), (0.50, 0.60)]),
        ("#2B8DEB", [(0.66, 0.56), (0.84, 0.72), (0.66, 0.82)]),
        ("#2B83E8", [(0.28, 0.57), (0.50, 0.43), (0.66, 0.56), (0.50, 0.64)]),
    ]

    for y in range(size):
        for x in range(size):
            px = (x + 0.5) / size
            py = (y + 0.5) / size
            color = transparent
            for hex_color, points in polygons:
                if point_in_polygon(px, py, points):
                    color = hex_to_rgba(hex_color)
            index = x * 4
            pixels[y][index:index + 4] = bytes(color)
    return pixels

def png_chunk(chunk_type, data):
    return (
        struct.pack("!I", len(data))
        + chunk_type
        + data
        + struct.pack("!I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )

def write_rgba_png(path, width, height, rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    compressed = zlib.compress(raw, level=9)
    png = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0)),
            png_chunk(b"IDAT", compressed),
            png_chunk(b"IEND", b""),
        ]
    )
    with open(path, "wb") as file_obj:
        file_obj.write(png)

def write_logo_png(path, size):
    pixels = render_logo_rgba(size)
    write_rgba_png(path, size, size, pixels)

class AssetManager:
    def __init__(self, root, script_dir, assets_dir):
        self.root = root
        self.script_dir = script_dir
        self.assets_dir = assets_dir
        self.logo_paths = {}
        self.logo_images = {}
        self.ctk_logo_images = {}
        self.init_logo_assets()

    def init_logo_assets(self):
        preferred_logo = os.path.join(self.assets_dir, "logo.png")
        try:
            os.makedirs(self.assets_dir, exist_ok=True)
            for key, size in {"badge": 60, "header": 24, "icon": 64}.items():
                if os.path.exists(preferred_logo):
                    path = preferred_logo
                else:
                    path = os.path.join(self.assets_dir, f"scrcpy_deck_logo_{size}.png")
                    if not os.path.exists(path):
                        write_logo_png(path, size)
                self.logo_paths[key] = path
                self.logo_images[key] = tk.PhotoImage(file=path)
                ctk_image = load_ctk_logo_image(path, size)
                if ctk_image is not None:
                    self.ctk_logo_images[key] = ctk_image
            self.apply_window_icon()
        except Exception:
            self.logo_paths = {}
            self.logo_images = {}
            self.ctk_logo_images = {}

    def apply_window_icon(self):
        icon_candidates = [
            os.path.join(self.assets_dir, "logo.ico"),
            os.path.join(self.assets_dir, "icon.ico"),
            os.path.join(self.script_dir, "icon.ico"),
        ]
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                    return
                except Exception:
                    pass
        try:
            if self.logo_images.get("icon"):
                self.root.iconphoto(True, self.logo_images["icon"])
        except Exception:
            pass
