"""Curated car-camping campgrounds within roughly 2 hours of San Francisco.

Recreation.gov entries carry the campground id from the recreation.gov URL
(``recreation.gov/camping/campgrounds/<id>``). ReserveCalifornia entries are
matched by park name at run time (``rc-search`` shows the resolved ids), so
they keep working even if the state renumbers facilities.

Drive times are rough, from downtown SF without traffic.
"""

from __future__ import annotations

CATALOG: dict[str, dict] = {
    # ---- recreation.gov ------------------------------------------------------
    "kirby-cove": {
        "name": "Kirby Cove (Golden Gate NRA)",
        "provider": "recreation.gov",
        "campground_id": "232491",
        "region": "Marin Headlands",
        "drive": "25 min",
        "notes": "5 sites on a beach under the Golden Gate Bridge; park and walk a short "
        "distance down a gravel road. Books out fast; seasonal.",
    },
    "pinnacles": {
        "name": "Pinnacles Campground (Pinnacles NP)",
        "provider": "recreation.gov",
        "campground_id": "234015",
        "region": "San Benito County",
        "drive": "2 h",
        "notes": "Large campground by the East Entrance with a pool in summer, condors, "
        "talus caves. Easiest of the list to get on short notice; very hot in summer.",
    },
    "liberty-glen": {
        "name": "Liberty Glen (Lake Sonoma)",
        "provider": "recreation.gov",
        "campground_id": "233537",
        "region": "Sonoma County",
        "drive": "1 h 45 min",
        "notes": "Army Corps campground on a ridge above Lake Sonoma; spacious sites, "
        "near Healdsburg wineries.",
    },
    # ---- ReserveCalifornia (state parks) --------------------------------------
    "samuel-p-taylor": {
        "name": "Samuel P. Taylor State Park",
        "provider": "reservecalifornia",
        "park": ["samuel p taylor"],
        "region": "Marin",
        "drive": "1 h",
        "notes": "Creekside redwood sites; close to Point Reyes. Very popular.",
    },
    "china-camp": {
        "name": "China Camp State Park",
        "provider": "reservecalifornia",
        "park": ["china camp"],
        "region": "Marin (San Rafael)",
        "drive": "35 min",
        "notes": "Walk-in sites a short carry from the lot; bay views, mountain biking.",
    },
    "steep-ravine": {
        "name": "Steep Ravine Cabins & Sites (Mount Tamalpais SP)",
        "provider": "reservecalifornia",
        "park": ["mount tamalpais"],
        "region": "Marin coast",
        "drive": "45 min",
        "notes": "Rustic cabins/sites on a bluff over the Pacific; the hardest booking in "
        "the Bay Area - exactly what this monitor is for.",
    },
    "mount-diablo": {
        "name": "Mount Diablo State Park (Juniper / Live Oak)",
        "provider": "reservecalifornia",
        "park": ["mount diablo"],
        "region": "East Bay",
        "drive": "1 h",
        "notes": "Juniper campground has sunset views across the Bay; hot and dry in summer, "
        "best in spring.",
    },
    "half-moon-bay": {
        "name": "Half Moon Bay State Beach (Francis Beach)",
        "provider": "reservecalifornia",
        "park": ["half moon bay"],
        "region": "San Mateo coast",
        "drive": "45 min",
        "notes": "Beachfront sites right behind the dunes, walk into town.",
    },
    "butano": {
        "name": "Butano State Park",
        "provider": "reservecalifornia",
        "park": ["butano"],
        "region": "San Mateo coast",
        "drive": "1 h 15 min",
        "notes": "Quiet redwood canyon near Pescadero; drive-in and walk-in sites.",
    },
    "portola-redwoods": {
        "name": "Portola Redwoods State Park",
        "provider": "reservecalifornia",
        "park": ["portola redwoods"],
        "region": "Santa Cruz Mountains",
        "drive": "1 h 15 min",
        "notes": "Deep in the redwoods off Alpine Rd; no cell service.",
    },
    "henry-cowell": {
        "name": "Henry Cowell Redwoods State Park",
        "provider": "reservecalifornia",
        "park": ["henry cowell"],
        "region": "Santa Cruz Mountains",
        "drive": "1 h 30 min",
        "notes": "Sandy pine-ridge campground near Felton and the Roaring Camp railroad.",
    },
    "new-brighton": {
        "name": "New Brighton State Beach",
        "provider": "reservecalifornia",
        "park": ["new brighton"],
        "region": "Santa Cruz (Capitola)",
        "drive": "1 h 30 min",
        "notes": "Bluff-top sites above the beach; walk to Capitola.",
    },
    "sunset-state-beach": {
        "name": "Sunset State Beach",
        "provider": "reservecalifornia",
        "park": ["sunset state beach", "sunset"],
        "region": "Santa Cruz County (Watsonville)",
        "drive": "1 h 45 min",
        "notes": "Sites in the dunes behind a long, uncrowded beach.",
    },
    "sugarloaf-ridge": {
        "name": "Sugarloaf Ridge State Park",
        "provider": "reservecalifornia",
        "park": ["sugarloaf ridge"],
        "region": "Sonoma Valley",
        "drive": "1 h 15 min",
        "notes": "Meadow campground with an observatory and Bald Mountain hike; near Kenwood "
        "wineries.",
    },
    "bothe-napa": {
        "name": "Bothe-Napa Valley State Park",
        "provider": "reservecalifornia",
        "park": ["bothe napa"],
        "region": "Napa Valley",
        "drive": "1 h 30 min",
        "notes": "Shady sites and a seasonal pool between St. Helena and Calistoga.",
    },
    "sonoma-coast": {
        "name": "Sonoma Coast State Park (Bodega Dunes / Wright's Beach)",
        "provider": "reservecalifornia",
        "park": ["sonoma coast"],
        "region": "Sonoma coast",
        "drive": "1 h 45 min",
        "notes": "Wright's Beach sites sit right on the sand; Bodega Dunes is sheltered in "
        "the dunes near Bodega Bay.",
    },
}
