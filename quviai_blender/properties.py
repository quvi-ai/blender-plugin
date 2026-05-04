from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import PropertyGroup

# (blender_id, display_name, api_value)
_STYLES = [
    ("no_style",           "No Style",           "no style"),
    ("Modern",             "Modern",             "Modern"),
    ("Modernist",          "Modernist",          "Modernist"),
    ("Art_Deco",           "Art Deco",           "Art Deco"),
    ("Art_Nouveau",        "Art Nouveau",        "Art Nouveau"),
    ("Baroque",            "Baroque",            "Baroque"),
    ("Bauhaus",            "Bauhaus",            "Bauhaus"),
    ("Chinese",            "Chinese",            "Chinese"),
    ("Classical",          "Classical",          "Classical"),
    ("Colonial",           "Colonial",           "Colonial"),
    ("Deconstructivist",   "Deconstructivist",   "Deconstructivist"),
    ("Expressionist",      "Expressionist",      "Expressionist"),
    ("Futuristic",         "Futuristic",         "Futuristic"),
    ("Gothic_Revival",     "Gothic Revival",     "Gothic Revival"),
    ("Industrial",         "Industrial",         "Industrial"),
    ("Islamic",            "Islamic",            "Islamic"),
    ("Japanese",           "Japanese",           "Japanese"),
    ("Landscape",          "Landscape",          "Landscape"),
    ("Mannerist",          "Mannerist",          "Mannerist"),
    ("Metabolist",         "Metabolist",         "Metabolist"),
    ("Neoclassical",       "Neoclassical",       "Neoclassical"),
    ("Neo_Gothic",         "Neo-Gothic",         "Neo-Gothic"),
    ("Postmodern",         "Postmodern",         "Postmodern"),
    ("Remodernism",        "Remodernism",        "Remodernism"),
    ("Rococo",             "Rococo",             "Rococo"),
    ("Romanesque",         "Romanesque",         "Romanesque"),
    ("Scandinavian",       "Scandinavian",       "Scandinavian"),
    ("Sustainable",        "Sustainable",        "Sustainable"),
    ("Victorian",          "Victorian",          "Victorian"),
    ("Aerial_Photography", "Aerial Photography", "Aerial Photography"),
    ("Cyberpunk",          "Cyberpunk",          "Cyberpunk"),
    ("Steampunk",          "Steampunk",          "Steampunk"),
    ("Gothic",             "Gothic",             "Gothic"),
    ("Gothic_Family",      "Gothic Family",      "Gothic Family"),
    ("Fantasy",            "Fantasy",            "Fantasy"),
    ("Cinematic",          "Cinematic",          "Cinematic"),
    ("Oil_Painting",       "Oil Painting",       "Oil Painting"),
    ("Watercolor",         "Watercolor",         "Watercolor"),
    ("Pixel_Art",          "Pixel Art",          "Pixel Art"),
    ("Pop_Art",            "Pop Art",            "Pop Art"),
    ("Cubism",             "Cubism",             "Cubism"),
    ("Sketch",             "Sketch",             "Sketch"),
    ("Line_Art",           "Line Art",           "Line Art"),
    ("Street_Art",         "Street Art",         "Street Art"),
    ("Tattoo_Art",         "Tattoo Art",         "Tattoo Art"),
    ("Origami",            "Origami",            "Origami"),
    ("Mosaic",             "Mosaic",             "Mosaic"),
    ("Engraving",          "Engraving",          "Engraving"),
    ("Monochrome",         "Monochrome",         "Monochrome"),
    ("Night_Photography",  "Night Photography",  "Night Photography"),
    ("Food_Photography",   "Food Photography",   "Food Photography"),
    ("Caricature",         "Caricature",         "Caricature"),
    ("Animation",          "Animation",          "Animation"),
    ("East_African_Art",   "East African Art",   "East African Art"),
    ("Assemblage_Art",     "Assemblage Art",     "Assemblage Art"),
    ("Automotive_Design",  "Automotive Design",  "Automotive Design"),
    ("Vampire",            "Vampire",            "Vampire"),
]

STYLE_ITEMS = [(s[0], s[1], "") for s in _STYLES]
STYLE_TO_API = {s[0]: s[2] for s in _STYLES}


class QuviAIProperties(PropertyGroup):
    """Per-scene QUVIAI state, stored in scene.quviai."""

    # --- Render-TD parameters ---
    prompt: StringProperty(
        name="Prompt",
        description="Text prompt describing the desired render",
        default="",
    )  # type: ignore[assignment]

    style: EnumProperty(
        name="Style",
        description="Architectural or artistic style",
        items=STYLE_ITEMS,
        default="no_style",
    )  # type: ignore[assignment]

    render_type: EnumProperty(
        name="Render Type",
        description="Architectural render type",
        items=[
            ("NONE",     "None",     ""),
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
            ("NONE",  "None",  ""),
            ("day",   "Day",   "Noon natural sunlight"),
            ("night", "Night", "Night artificial lighting"),
        ],
        default="day",
    )  # type: ignore[assignment]

    weather: EnumProperty(
        name="Weather",
        description="Weather conditions",
        items=[
            ("NONE",   "None",   ""),
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
