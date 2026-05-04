from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

# (blender_id, display_name, api_value)
_ARCH_STYLES = [
    ("no_style",                      "No Style",        "no style"),
    ("Art_Deco_Architecture",         "Art Deco",        "Art Deco Architecture"),
    ("Art_Nouveau_Architecture",      "Art Nouveau",     "Art Nouveau Architecture"),
    ("Baroque_Architecture",          "Baroque",         "Baroque Architecture"),
    ("Bauhaus_Architecture",          "Bauhaus",         "Bauhaus Architecture"),
    ("Chinese_Architecture",          "Chinese",         "Chinese Architecture"),
    ("Classical_Architecture",        "Classical",       "Classical Architecture"),
    ("Colonial_Architecture",         "Colonial",        "Colonial Architecture"),
    ("Deconstructivist_Architecture", "Deconstructivist","Deconstructivist Architecture"),
    ("Expressionist_Architecture",    "Expressionist",   "Expressionist Architecture"),
    ("Futurist_Architecture",         "Futurist",        "Futurist Architecture"),
    ("Gothic_Revival_Architecture",   "Gothic Revival",  "Gothic Revival Architecture"),
    ("Industrial_Architecture",       "Industrial",      "Industrial Architecture"),
    ("Islamic_Architecture",          "Islamic",         "Islamic Architecture"),
    ("Japanese_Architecture",         "Japanese",        "Japanese Architecture"),
    ("Landscape_Architecture",        "Landscape",       "Landscape Architecture"),
    ("Line_Art_Arch",                 "Line Art",        "sai-line art_Uncategorized"),
    ("Mannerist_Architecture",        "Mannerist",       "Mannerist Architecture"),
    ("Metabolist_Architecture",       "Metabolist",      "Metabolist Architecture"),
    ("Modern_Architecture",           "Modern",          "Modern Architecture"),
    ("Modernist_Architecture",        "Modernist",       "Modernist Architecture"),
    ("Neoclassical_Architecture",     "Neoclassical",    "Neoclassical Architecture"),
    ("Neo_Gothic_Architecture",       "Neo-Gothic",      "Neo-Gothic Architecture"),
    ("Postmodern_Architecture",       "Postmodern",      "Postmodern Architecture"),
    ("Remodernism_Architecture",      "Remodernism",     "Remodernism_Architecture"),
    ("Rococo_Architecture",           "Rococo",          "Rococo Architecture"),
    ("Romanesque_Architecture",       "Romanesque",      "Romanesque Architecture"),
    ("Scandinavian_Design",           "Scandinavian",    "Scandinavian Design"),
    ("Sustainable_Architecture",      "Sustainable",     "Sustainable Architecture"),
    ("Victorian_Architecture",        "Victorian",       "Victorian Architecture"),
]

_GENERAL_STYLES = [
    ("no_style",               "No Style",            "no style"),
    ("3D_Animation",           "3D Animation",        "3D Animation"),
    ("Action_Films",           "Action Films",        "Action Films"),
    ("Aerial_Photography",     "Aerial Photography",  "Aerial Photography"),
    ("African_Mask_Art",       "African Mask Art",    "African Mask Art"),
    ("Analytical_Cubism",      "Analytical Cubism",   "Analytical Cubism"),
    ("Animation",              "Animation",           "Animation"),
    ("Art_Mobile_Apps",        "Art for Mobile Apps", "Art for Mobile Apps"),
    ("Assemblage_Art",         "Assemblage Art",      "Assemblage Art"),
    ("Automotive_Design",      "Automotive Design",   "Automotive Design"),
    ("Caricature",             "Caricature",          "Caricature"),
    ("Ceramics",               "Ceramics",            "Ceramics"),
    ("Cinematic",              "Cinematic",           "sai-cinematic_Uncategorized"),
    ("Aardman",                "Aardman",             "Aardman_Uncategorized"),
    ("Animated_Corpse",        "Animated Corpse",     "Animated Corpse_Animation"),
    ("Cosplay_Design",         "Cosplay Design",      "Cosplay Design"),
    ("Cubism",                 "Cubism",              "Cubism"),
    ("Cyberpunk",              "Cyberpunk",           "Cyberpunk"),
    ("Digital_Animation",      "Digital Animation",   "Digital Animation"),
    ("Artware_Variant",        "Artware Variant",     "Artware Variant_Sci-Fi_Graffiti_Digital Media"),
    ("East_African_Art",       "East African Art",    "East African Art"),
    ("Engraving",              "Engraving",           "Engraving"),
    ("Expressionist_Painting", "Expressionist",       "Expressionist painting"),
    ("Fantasy",                "Fantasy",             "Fantasy"),
    ("Art_for_Fashion",        "Art for Fashion",     "Art for Fashion Industry"),
    ("Food_Photography",       "Food Photography",    "Food Photography"),
    ("Futuristic_SciFi",       "Futuristic Sci-Fi",   "futuristic-futuristic_Sci-Fi"),
    ("Addams_Family",          "Addams Family",       "Addams Family_Portraiture_Horror"),
    ("Gothic",                 "Gothic",              "misc-gothic_Gothic"),
    ("Albrecht_Durer",         "Albrecht Dürer",      "Albrecht Durer"),
    ("Ice_Sculpture",          "Ice Sculpture",       "Ice Sculpture"),
    ("Light_Art",              "Light Art",           "Light Art"),
    ("Line_Art",               "Line Art",            "sai-line art_Uncategorized"),
    ("Art_with_Metalwork",     "Art with Metalwork",  "Art with Metalwork"),
    ("BW_Photography",         "B&W Photography",     "Black and White Photography"),
    ("Mosaic",                 "Mosaic",              "Mosaic"),
    ("Motion_Design",          "Motion Design",       "Motion Design"),
    ("Night_Photography",      "Night Photography",   "Night Photography"),
    ("Oil_Painting",           "Oil Painting",        "Oil Painting"),
    ("Origami",                "Origami",             "sai-origami_Uncategorized"),
    ("Photographic",           "Photographic",        "sai-photographic_Photography"),
    ("Pixel_Art",              "Pixel Art",           "Pixel Art"),
    ("Pop_Art",                "Pop Art",             "Pop art style"),
    ("Robotics_Art",           "Robotics Art",        "Robotics Art"),
    ("Sculpture",              "Sculpture",           "Sculpture"),
    ("Steampunk",              "Steampunk",           "Steampunk"),
    ("Street_Art",             "Street Art",          "Street Art"),
    ("Tattoo_Art",             "Tattoo Art",          "American Traditional_Retro_Tattoo Art"),
    ("Vampire",                "Bloodthirsty Vampire","Bloodthirsty Vampire_Horror"),
]

ARCH_STYLE_ITEMS  = [(s[0], s[1], "") for s in _ARCH_STYLES]
GENERAL_STYLE_ITEMS = [(s[0], s[1], "") for s in _GENERAL_STYLES]

# Combined lookup: blender_id → api_value (arch ids take precedence on collision)
STYLE_TO_API: dict[str, str] = {s[0]: s[2] for s in _GENERAL_STYLES}
STYLE_TO_API.update({s[0]: s[2] for s in _ARCH_STYLES})


class QuviAIProperties(PropertyGroup):
    """Per-scene QUVIAI state, stored in scene.quviai."""

    # --- Category ---
    style_category: EnumProperty(
        name="Category",
        description="Architectural or general illustration",
        items=[
            ("architectural", "Architectural", "Architecture visualization styles with render-type controls"),
            ("general",       "General",       "Illustration and artistic styles"),
        ],
        default="architectural",
    )  # type: ignore[assignment]

    # --- Style (per-category) ---
    arch_style: EnumProperty(
        name="Style",
        description="Architectural style",
        items=ARCH_STYLE_ITEMS,
        default="no_style",
    )  # type: ignore[assignment]

    general_style: EnumProperty(
        name="Style",
        description="Illustration / artistic style",
        items=GENERAL_STYLE_ITEMS,
        default="no_style",
    )  # type: ignore[assignment]

    # --- Prompt (stored as a Blender Text block for multiline editing) ---
    prompt_text: PointerProperty(
        name="Prompt",
        description="Text block containing the render prompt (edit in Text Editor)",
        type=bpy.types.Text,
    )  # type: ignore[assignment]

    render_type: EnumProperty(
        name="Render Type",
        description="Architectural render type",
        items=[
            ("exterior", "Exterior", "Exterior architectural render"),
            ("interior", "Interior", "Interior architectural render"),
            ("site",     "Site",     "Site plan aerial view"),
        ],
        default="exterior",
    )  # type: ignore[assignment]

    day_time: EnumProperty(
        name="Time of Day",
        description="Lighting conditions",
        items=[
            ("day",   "Day",   "Noon natural sunlight"),
            ("night", "Night", "Night artificial lighting"),
        ],
        default="day",
    )  # type: ignore[assignment]

    weather: EnumProperty(
        name="Weather",
        description="Weather conditions",
        items=[
            ("sunny",  "Sunny",  ""),
            ("cloudy", "Cloudy", ""),
            ("rainy",  "Rainy",  ""),
            ("snowy",  "Snowy",  ""),
            ("windy",  "Windy",  ""),
            ("foggy",  "Foggy",  ""),
        ],
        default="sunny",
    )  # type: ignore[assignment]

    # --- Task state ---
    is_rendering: BoolProperty(default=False)  # type: ignore[assignment]
    status: StringProperty(default="")  # type: ignore[assignment]
    progress: FloatProperty(default=0.0, min=0.0, max=100.0)  # type: ignore[assignment]
    result_image_name: StringProperty(default="")  # type: ignore[assignment]


def register() -> None:
    bpy.utils.register_class(QuviAIProperties)
    bpy.types.Scene.quviai = bpy.props.PointerProperty(type=QuviAIProperties)


def unregister() -> None:
    del bpy.types.Scene.quviai
    bpy.utils.unregister_class(QuviAIProperties)
