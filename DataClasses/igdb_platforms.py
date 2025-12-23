# IGDB Platform ID mappings
# Maps common platform names to their IGDB platform IDs
# Reference: https://api-docs.igdb.com/#platform

PLATFORM_MAPPINGS = {
    # PlayStation
    'ps5': 167,
    'playstation 5': 167,
    'ps4': 48,
    'playstation 4': 48,
    'ps3': 9,
    'playstation 3': 9,
    'ps2': 8,
    'playstation 2': 8,
    'ps1': 7,
    'playstation 1': 7,
    'playstation': 7,
    'psx': 7,
    'ps vita': 46,
    'vita': 46,
    'psp': 38,

    # Xbox
    'xbox series x|s': 169,
    'xbox series': 169,
    'xbox one': 49,
    'xbox 360': 12,
    'xbox': 11,
    'original xbox': 11,

    # Nintendo
    'switch': 130,
    'nintendo switch': 130,
    'wii u': 41,
    'wii': 5,
    'gamecube': 21,
    'n64': 4,
    'nintendo 64': 4,
    'snes': 19,
    'super nintendo': 19,
    'nes': 18,
    'nintendo entertainment system': 18,
    '3ds': 37,
    'nintendo 3ds': 37,
    'ds': 20,
    'nintendo ds': 20,
    'game boy advance': 24,
    'gba': 24,
    'game boy color': 22,
    'gbc': 22,
    'game boy': 33,

    # PC
    'pc': 6,
    'windows': 6,
    'mac': 14,
    'macos': 14,
    'linux': 3,

    # Mobile
    'ios': 39,
    'iphone': 39,
    'ipad': 39,
    'android': 34,

    # Retro
    'sega genesis': 29,
    'genesis': 29,
    'mega drive': 29,
    'dreamcast': 23,
    'saturn': 32,
    'sega saturn': 32,
    'master system': 64,
    'atari 2600': 59,
    'atari': 59,
}


def get_platform_id(platform_name):
    if not platform_name:
        return None

    platform_lower = platform_name.lower().strip()
    return PLATFORM_MAPPINGS.get(platform_lower)


def get_supported_platforms():
    return sorted(set(PLATFORM_MAPPINGS.keys()))
