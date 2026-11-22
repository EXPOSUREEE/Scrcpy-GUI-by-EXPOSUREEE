import json
import os
from dataclasses import dataclass

@dataclass
class DeviceInfo:
    serial: str
    state: str = "unknown"
    transport: str = "usb"
    brand: str = ""
    manufacturer: str = ""
    model: str = ""
    product: str = ""
    device: str = ""
    market_name: str = ""
    display_name: str = ""
    hardware_serial: str = ""

def load_device_name_map(script_dir: str) -> dict:
    map_path = os.path.join(script_dir, "data", "device_name_map.json")
    if os.path.exists(map_path):
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load device_name_map.json: {e}")
    return {}

def normalize_brand(value: str) -> str:
    if not value:
        return ""
    return value.strip().title()

def lookup_marketing_name(brand: str, manufacturer: str, model: str, mapping: dict) -> str:
    b = (brand or manufacturer).lower()
    if b in mapping:
        return mapping[b].get(model, "")
    return ""

def build_display_name(d: DeviceInfo, mapping: dict) -> str:
    name = d.market_name
    brand = normalize_brand(d.brand) or normalize_brand(d.manufacturer)
    model = d.model or d.product or d.device

    if not name:
        name = lookup_marketing_name(d.brand, d.manufacturer, d.model, mapping)

    if not name:
        if brand and model:
            if model.lower().startswith(brand.lower()):
                name = model
            else:
                name = f"{brand} {model}"
        elif model:
            name = model
        elif brand:
            name = brand
            
    if not name:
        short_serial = d.serial[:6]
        name = f"Android Device {short_serial}"

    if brand:
        brand_prefix = f"{brand} {brand}".lower()
        if name.lower().startswith(brand_prefix):
            name = name[len(brand)+1:].strip()

    transport_label = "USB"
    if d.transport == "wireless":
        transport_label = "Wireless"
    elif d.transport == "emulator":
        transport_label = "Emulator"
        
    d.display_name = f"{name} \u00b7 {transport_label}"
    return d.display_name
