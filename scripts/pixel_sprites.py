"""Pure-SVG uniform-grid pixel-art sprite compiler with horizontal run-length merging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PixelRect:
    """Merged horizontal pixel span for compact crisp-edge SVG output."""

    x: int
    y: int
    w: int
    h: int
    fill: str


SPRITE_PALETTE: dict[str, str] = {
    "K": "#121622",  # ink outline
    "W": "#F8FAFC",  # crisp highlight white
    "S": "#94A3B8",  # steel / slate
    "D": "#475569",  # dark steel / stone
    "H": "#7DD3FC",  # plasma cyan highlight
    "B": "#38BDF8",  # hero cyan
    "I": "#1D4ED8",  # cobalt cloak
    "N": "#1E293B",  # dark armor
    "F": "#FDBA74",  # skin tone
    "L": "#A7F3D0",  # mint lime highlight
    "G": "#34D399",  # emerald
    "E": "#059669",  # deep emerald
    "A": "#FEF08A",  # solar flare yellow
    "Y": "#FBBF24",  # amber gold
    "O": "#D97706",  # deep gold / wood
    "T": "#FDA4AF",  # bright rose highlight
    "R": "#F43F5E",  # crimson fire
    "M": "#9F1239",  # deep crimson
    "P": "#A78BFA",  # arcane purple
    "V": "#6D28D9",  # deep violet
    "C": "#FFFFFF",  # cloud white
}

# 5x9 Wall Torch (uniform 4px world scale -> 20x36)
WALL_TORCH: tuple[str, ...] = (
    "..A..",
    ".AYY.",
    ".RYY.",
    ".MRM.",
    "KKKKK",
    ".KOD.",
    "..K..",
    "..K..",
    "..K..",
)

# 8x8 Sky Celestials & Cloud
PIXEL_MOON: tuple[str, ...] = (
    "..AAAA..",
    ".AYYY...",
    "AYYY....",
    "YY......",
    "YY......",
    "AYYY....",
    ".AYYY...",
    "..AAAA..",
)

PIXEL_SUN: tuple[str, ...] = (
    "...AA...",
    ".Y.YY.Y.",
    "..AAAA..",
    "AYYYYYYA",
    "AYYYYYYA",
    "..AAAA..",
    ".Y.YY.Y.",
    "...AA...",
)

PIXEL_CLOUD: tuple[str, ...] = (
    "....CCCC......",
    "..CCCCCCCC....",
    ".CCCCCCCCCC...",
    "CCCCCCCCCCCCCC",
    ".SSSSSSSSSSSS.",
)

# 20x16 Right-Facing Side-Profile Hooded Hero swinging an angled cyan plasma blade
HERO_ARCHITECT: tuple[str, ...] = (
    ".....KKKKKK.........",
    "....KIIIIIIKK.......",
    "...KIIIIHHHHIK......",
    "..KIIIIIKKKKKK......",
    "..KIIIIKHHHHBK....W.",
    "..KIIIIKKKKKK....WH.",
    "...KKIIKFFKK....WHB.",
    "..KKIIIIINNNK..WHB..",
    ".KIIIIIINNNNNKWHB...",
    "KIIIINNNNNNNNYKB....",
    "KIIKNNNNNNNNKYK.....",
    ".KK.KNNNNNNNK.......",
    "....KNNNNKNNK.......",
    "....KNNK..KNNK......",
    "...KNNK....KNNK.....",
    "...KKKK....KKKK.....",
)

# 9x9 Side-Facing Emerald Spark Familiar (facing right)
COMPANION_SPARK: tuple[str, ...] = (
    "...KKKK..",
    "..KLLLLK.",
    ".KGGGGGGK",
    "KGGGGGWGK",
    "KGGGGGGGK",
    "KGGEEEEGK",
    ".KKEEEEK.",
    "..KKKKKK.",
    ".........",
)

# 8x5 Arcing Pixel Blade Wave (rightward) & Boss Ember Blast (leftward)
HERO_WAVE: tuple[str, ...] = (
    "..KKK...",
    ".BHHWK..",
    "BBHHWWK.",
    ".BHHWK..",
    "..KKK...",
)

BOSS_WAVE: tuple[str, ...] = (
    "...KKK..",
    "..KYYRR.",
    ".KAAYYRM",
    "..KYYRR.",
    "...KKK..",
)

# 7x7 Pixel Impact Spark
SWORD_CLASH: tuple[str, ...] = (
    "...R...",
    ".R.A.R.",
    "..RYR..",
    "RAYWYAR",
    "..RYR..",
    ".R.A.R.",
    "...R...",
)

# 22x16 Left-Facing Side-Profile Boss Sprites (tail/wings right, jaws/weapon left)
BOSS_SPRITES: dict[str, tuple[str, ...]] = {
    "nullpointer_wyrm": (
        "......KK...KK...KK....",
        ".....KRRK.KRYKKMMMK...",
        "....KRRRRKKRYYMMMMMK..",
        "..KKRWWYRRRRRMMMMMMMM.",
        ".KRRRRRRRRRRRMMMMKMMMK",
        "KRRRRMMMMRRRRMMMM.KMK.",
        "KWWK.KRRRRYYYMMMM.....",
        ".KK...KRRRYYYYMMK.....",
        "......KRRRYYYYRRK.....",
        ".....KMRRRYYYYRRK.....",
        "....KMRRRRRRRRRRRK....",
        "...KMMK.KRRRRRKMRRK...",
        "...KKK..KMRK.KKRMMMK..",
        "........KMK....KMRRK..",
        ".......KMMK.....KKKK..",
        ".......KKKK...........",
    ),
    "merge_golem": (
        ".....KKKKKKKK.........",
        "....KSSSSSSSSKK.......",
        "...KSDDDDDDDDSSK......",
        "...KSDAAKAAKDDDSK.....",
        "..KKSDDDDDDDDDSSKK....",
        ".KSSSDDDYYYYDDDSSSK...",
        "KSSSKSDDYAAYDDSSDDDK..",
        "KDDKKSDDYYYYDDSSDDDK..",
        "KKKK.KSDDDDDDDSSDDK...",
        "......KSSSSSSSSSSK....",
        ".....KSSDDDDDDSSSK....",
        ".....KSDDK..KDDDSK....",
        "....KSSDK....KDDSSK...",
        "....KSSK......KSSSK...",
        "...KKKKK......KKKKK...",
        "......................",
    ),
    "hallucination_phantom": (
        ".....KKKKKKK..........",
        "...KKPPPPPPPKK........",
        "..KPPPVVVVVPPPK.......",
        ".KPPVPKWWPKVPPPK......",
        ".KPPPKKHHKKVPPPK......",
        ".KPPPPPPPPPVPPPK......",
        "KPPVK.KPPPPVVPPPK.....",
        "KHHK...KPPPVVVPPPK....",
        ".KK....KPPPPVVVPPPK...",
        ".......KPPPVVVVVPPPK..",
        "......KPPPKVPPPKKPPPK.",
        "......KPPK.KPPK..KPK..",
        ".....KPPK..KVK....K...",
        ".....KPK...KK.........",
        "......K...............",
        "......................",
    ),
    "legacy_monolith": (
        "...KK.KK.KK.KK........",
        "..KKKKKKKKKKKKK.......",
        "..KDDDDDDDDDDDK.......",
        "..KDDADDDDDADDK.......",
        "..KDDDDDDDDDDDK.......",
        ".KDDKRRRRRRRKDDK......",
        ".KDDKRWWWWWRKDDK......",
        ".KDDKRWKKKWRKDDK......",
        ".KDDKRRRRRRRKDDK......",
        "..KDDDDGGDDDDDK.......",
        "..KDDGGGGGGGGDK.......",
        "..KDDSSSSSSSSDK.......",
        ".KDDSSKKKKKKSSDK......",
        ".KDDSSK....KSSDK......",
        ".KKKKKKKKKKKKKKK......",
        "......................",
    ),
}

# 10x10 Achievement Badge Sprites (rendered cleanly at 3x = 30x30)
QUEST_SPRITES: dict[str, tuple[str, ...]] = {
    "genesis_commit": (
        "....KK....",
        "...KGGK...",
        "..KGGWGK..",
        "...KGGK...",
        "....KK....",
        "..KGGGGK..",
        "...KGGK...",
        "..KOOOOOK.",
        ".KOOOOOOOK",
        "..KKKKKKK.",
    ),
    "shipwright": (
        "....KK....",
        "...KWWK...",
        "..KWWWWK..",
        "..KWWWWK..",
        "....KK....",
        "KOOOOOOOOK",
        ".KOOOOOOK.",
        ".KODDDDOK.",
        "..KKKKKK..",
        ".KBBBBBBK.",
    ),
    "doc_architect": (
        "..KKKKKK..",
        ".KWWWWWWK.",
        ".KWBBBBWK.",
        ".KWWWWWWK.",
        ".KWSSSWWK.",
        ".KWWWWWWK.",
        ".KWSSSWWK.",
        ".KWWWWWWK.",
        "..KKKKKK..",
        "..........",
    ),
    "ci_guardian": (
        ".KKKKKKKK.",
        "KBBBBBBBBK",
        "KBBGGGGGBK",
        "KBBGGGGGBK",
        "KBGGWGGGBK",
        "KBBGGGGGBK",
        ".KBBBBBBK.",
        "..KBBBBK..",
        "...KBBK...",
        "....KK....",
    ),
    "polyglot_stack": (
        "....KK....",
        "...KBBK...",
        "..KBPBPK..",
        ".KBPWWPPK.",
        "KBPPWWPPYK",
        ".KPPGGPYK.",
        "..KPGPYK..",
        "...KGYK...",
        "....KK....",
        "..........",
    ),
    "club_500": (
        "....KK....",
        "...KRRK...",
        "..KRYYRK..",
        ".KRYWWYRK.",
        ".KRYYYYRK.",
        ".KRRRRRRK.",
        "..KMMMMK..",
        "...KMMK...",
        "....KK....",
        "..........",
    ),
    "week_sprint": (
        ".....KKK..",
        "....KYYK..",
        "...KYYK...",
        "..KYYYK...",
        ".KYYYYYYK.",
        "...KKYYK..",
        "...KYYK...",
        "..KYYK....",
        "..KKK.....",
        "..........",
    ),
    "first_merge": (
        ".KK....KK.",
        "KYYK..KYYK",
        ".KKK..KKK.",
        "..KYYYYK..",
        "...KYYK...",
        "...KYYK...",
        "...KYYK...",
        "..KYYYYK..",
        "...KKKK...",
        "..........",
    ),
    "builder_1k": (
        ".KKKKKKKK.",
        "KYYYYYYYYK",
        ".KKYYYYKK.",
        "...KYYK...",
        "..KSSSSK..",
        ".KSSSSSSK.",
        "KSSSSSSSSK",
        ".KKKKKKKK.",
        "..........",
        "..........",
    ),
    "fortnight_streak": (
        "......KK..",
        "....KKRRK.",
        "...KRRYYK.",
        "..KRYYYYK.",
        ".KRRYYKK..",
        ".KRRK.....",
        ".KRK......",
        "KKK.......",
        "..........",
        "..........",
    ),
    "os_ally": (
        ".KKKKKKKK.",
        ".KPPPPPPK.",
        ".KPWWWWPK.",
        ".KPWGGWPK.",
        ".KPPPPPPK.",
        ".KPK..KPK.",
        ".KPK......",
        ".KKK......",
        "..........",
        "..........",
    ),
    "community_signal": (
        "....KK....",
        "...KYYK...",
        "KKKYYYYKKK",
        "KYYYYYYYYK",
        ".KYYWWYYK.",
        "..KYYYYK..",
        ".KYYKKYYK.",
        "KKK....KKK",
        "..........",
        "..........",
    ),
}


def compile_pixel_grid(
    grid: tuple[str, ...],
    *,
    scale: int = 4,
    ox: int = 0,
    oy: int = 0,
    locked_color: str | None = None,
) -> list[PixelRect]:
    """Compile ASCII pixel grid into RLE-merged PixelRect rectangles."""
    rects: list[PixelRect] = []
    for row_idx, row in enumerate(grid):
        col = 0
        width = len(row)
        while col < width:
            ch = row[col]
            if ch == "." or ch not in SPRITE_PALETTE:
                col += 1
                continue
            run_end = col + 1
            if locked_color is not None:
                while run_end < width and row[run_end] != "." and row[run_end] in SPRITE_PALETTE:
                    run_end += 1
                fill = locked_color
            else:
                while run_end < width and row[run_end] == ch:
                    run_end += 1
                fill = SPRITE_PALETTE[ch]
            rects.append(
                PixelRect(
                    x=ox + col * scale,
                    y=oy + row_idx * scale,
                    w=(run_end - col) * scale,
                    h=scale,
                    fill=fill,
                )
            )
            col = run_end
    return rects
