"""
Temporary snapshot seed for the currently generated CarbonSnap forum Neo4j graph.

This file intentionally does not replace seed_recycling_graph.py because this
snapshot is generated from the experimental open forum graph and may need review.

Usage from backend/:
  python scripts/seed_forum_graph_snapshot.py --clear-first
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from scripts.clear_recycling_graph import clear_graph
from scripts.seed_recycling_graph import apply_schema, read_neo4j_env

UNIQUE_KEYS = {
    "Claim": "id",
    "DisposalMethod": "name",
    "Entity": "normalized_name",
    "Evidence": "id",
    "FacilityType": "name",
    "ForumPost": "post_id",
    "Item": "name",
    "KnowledgeChunk": "id",
    "Material": "name",
    "RelationFact": "id",
    "RelationType": "key",
    "Risk": "name",
    "Rule": "id",
}

GRAPH_NODES = [
    {
        "ref": "Claim:claim-0871cf1fd09dc16773ac",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.133000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.9,
            "id": "claim-0871cf1fd09dc16773ac",
            "text": "Apply electrical tape to lithium-based battery terminals to ensure safe storage before disposal.",
            "stance": "supports",
            "raw_predicate": "require terminal protection",
        },
    },
    {
        "ref": "Claim:claim-09c84fff162315a2f40b",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.483000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "confidence": 0.9,
            "id": "claim-09c84fff162315a2f40b",
            "text": "The author transformed a plain cardboard mailer into a functional gift box overnight.",
            "stance": "supports",
            "raw_predicate": "converts to",
        },
    },
    {
        "ref": "Claim:claim-0a7a2b01de2b3a4c8c15",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "canonical_relation": "has",
            "confidence": 0.9,
            "id": "claim-0a7a2b01de2b3a4c8c15",
            "text": "not everything in an e-waste pile is actually waste.",
            "stance": "supports",
            "raw_predicate": "contains",
        },
    },
    {
        "ref": "Claim:claim-17003b5804a9f4bcd6f0",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.274000000+00:00",
            "canonical_relation": "enhances",
            "confidence": 0.9,
            "id": "claim-17003b5804a9f4bcd6f0",
            "text": "A low-buy start is genuinely underrated for anyone setting up a dorm or small apartment.",
            "stance": "supports",
            "raw_predicate": "enhances",
        },
    },
    {
        "ref": "Claim:claim-170ee655f7da80bb32ec",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "canonical_relation": "should_be_documented_via",
            "confidence": 0.8,
            "id": "claim-170ee655f7da80bb32ec",
            "text": "Maintain a phone note listing nearby battery recycling spots to streamline the final collection "
            "step.",
            "stance": "supports",
            "raw_predicate": "should be documented via",
        },
    },
    {
        "ref": "Claim:claim-20419b91d26d9cd75c7a",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.812000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "confidence": 0.9,
            "id": "claim-20419b91d26d9cd75c7a",
            "text": "The author replaced the constant stream of disposable batteries in small household devices with "
            "rechargeable ones.",
            "stance": "supports",
            "raw_predicate": "replace",
        },
    },
    {
        "ref": "Claim:claim-207f5f2d2dae675b0870",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "canonical_relation": "exhibits_aesthetic",
            "confidence": 0.85,
            "id": "claim-207f5f2d2dae675b0870",
            "text": "What I liked most was that it still looked handmade, not overly polished.",
            "stance": "supports",
            "raw_predicate": "exhibits aesthetic",
        },
    },
    {
        "ref": "Claim:claim-228e851b2640da88f897",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "canonical_relation": "is_unnecessary_replacement_for",
            "confidence": 0.85,
            "id": "claim-228e851b2640da88f897",
            "text": "You should try this low-effort method before buying a new organizer.",
            "stance": "warns",
            "raw_predicate": "is unnecessary replacement for",
        },
    },
    {
        "ref": "Claim:claim-247c389eb5ceb92a8dfd",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "canonical_relation": "encourages_reuse_for",
            "confidence": 0.9,
            "id": "claim-247c389eb5ceb92a8dfd",
            "text": "Save this idea if you also have too many clean plastic bottles at home and want a festive excuse "
            "to reuse them.",
            "stance": "supports",
            "raw_predicate": "encourages reuse for",
        },
    },
    {
        "ref": "Claim:claim-2bdbcb9993bdb7da3870",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "canonical_relation": "may_only_need",
            "confidence": 0.85,
            "id": "claim-2bdbcb9993bdb7da3870",
            "text": "One keyboard just needed dust removal and a new cable, while the power bank definitely belongs in "
            "proper recycling.",
            "stance": "supports",
            "raw_predicate": "may only need",
        },
    },
    {
        "ref": "Claim:claim-2e9eaeeff7a42791490a",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "canonical_relation": "reduces_waste_during",
            "confidence": 0.9,
            "id": "claim-2e9eaeeff7a42791490a",
            "text": "Doing a quick category check first makes the final drop-off smarter and less wasteful.",
            "stance": "supports",
            "raw_predicate": "reduces waste during",
        },
    },
    {
        "ref": "Claim:claim-30683ba114e0b9811a62",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.470000000+00:00",
            "canonical_relation": "forms_primary_material_for",
            "confidence": 0.95,
            "id": "claim-30683ba114e0b9811a62",
            "text": "I ended up turning a clear plastic bottle into a mini lantern with a soft red glow inside.",
            "stance": "supports",
            "raw_predicate": "forms primary material for",
        },
    },
    {
        "ref": "Claim:claim-324a331faa753d9fd9ea",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.991000000+00:00",
            "canonical_relation": "compatible_with",
            "confidence": 0.8,
            "id": "claim-324a331faa753d9fd9ea",
            "text": "A small flashlight was initially switched to rechargeable batteries due to its frequent use.",
            "stance": "supports",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Claim:claim-3362c8088f9131c433d3",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.581000000+00:00",
            "canonical_relation": "wrapped_with",
            "confidence": 0.9,
            "id": "claim-3362c8088f9131c433d3",
            "text": "A sturdy cardboard mailer was covered using kraft paper to achieve a neat appearance.",
            "stance": "supports",
            "raw_predicate": "wrapped with",
        },
    },
    {
        "ref": "Claim:claim-34fcddb9609f33da510c",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "canonical_relation": "accumulates",
            "confidence": 0.9,
            "id": "claim-34fcddb9609f33da510c",
            "text": "Plastic bottles, snack wrappers, and cans have accumulated near the benches and bike parking "
            "area.",
            "stance": "supports",
            "raw_predicate": "accumulates_debris",
        },
    },
    {
        "ref": "Claim:claim-363504b805f9bb8b6dcc",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.494000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.9,
            "id": "claim-363504b805f9bb8b6dcc",
            "text": "Finally, I placed a small LED light inside and turned it on after dark.",
            "stance": "supports",
            "raw_predicate": "requires illumination from",
        },
    },
    {
        "ref": "Claim:claim-36f97362e819d72b5fe6",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.612000000+00:00",
            "canonical_relation": "improve",
            "confidence": 0.95,
            "id": "claim-36f97362e819d72b5fe6",
            "text": "Making simple printed labels for each bin made my family recycle properly and solved our kitchen "
            "sorting problem.",
            "stance": "supports",
            "raw_predicate": "improve",
        },
    },
    {
        "ref": "Claim:claim-3e920eb430edee8050ca",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.129000000+00:00",
            "canonical_relation": "keeps_clear",
            "confidence": 0.85,
            "id": "claim-3e920eb430edee8050ca",
            "text": "Keeping surfaces clear makes the room feel calmer by default.",
            "stance": "supports",
            "raw_predicate": "keeps clear",
        },
    },
    {
        "ref": "Claim:claim-3fd9ce5ebae2e41b6c22",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.574000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "confidence": 0.9,
            "id": "claim-3fd9ce5ebae2e41b6c22",
            "text": "For a no-spend fix using something I already had at home, it worked incredibly well.",
            "stance": "supports",
            "raw_predicate": "provides accessible solution for",
        },
    },
    {
        "ref": "Claim:claim-4338d1a98cd7523bfb46",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "canonical_relation": "organizes_on",
            "confidence": 0.85,
            "id": "claim-4338d1a98cd7523bfb46",
            "text": "Positioning the holder on the countertop keeps frequently used spatulas and wooden spoons easily "
            "accessible while tidying the space.",
            "stance": "supports",
            "raw_predicate": "organizes on",
        },
    },
    {
        "ref": "Claim:claim-4366ba9358dbc38e870c",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "canonical_relation": "prioritize",
            "confidence": 0.9,
            "id": "claim-4366ba9358dbc38e870c",
            "text": "Focusing on a clearer labeling system matters more than purchasing aesthetically pleasing bins.",
            "stance": "supports",
            "raw_predicate": "prioritize",
        },
    },
    {
        "ref": "Claim:claim-455d31e095a2f52c5dde",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.864000000+00:00",
            "canonical_relation": "aims_to_separate",
            "confidence": 0.85,
            "id": "claim-455d31e095a2f52c5dde",
            "text": "I am hoping to separate out obvious recyclables instead of treating everything as mixed trash.",
            "stance": "supports",
            "raw_predicate": "aims_to_separate",
        },
    },
    {
        "ref": "Claim:claim-4588a9d695ff9e43e689",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "canonical_relation": "is_expedited_by",
            "confidence": 0.85,
            "id": "claim-4588a9d695ff9e43e689",
            "text": "Grouping batteries by size and securing hazardous terminals beforehand significantly reduces "
            "drop-off time.",
            "stance": "supports",
            "raw_predicate": "is expedited by",
        },
    },
    {
        "ref": "Claim:claim-4748885f5ecbdb69f0e6",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "canonical_relation": "identifies",
            "confidence": 0.8,
            "id": "claim-4748885f5ecbdb69f0e6",
            "text": "Even if you do not fix anything today, you will at least know what needs repair, what can be "
            "donated, and what should be recycled responsibly.",
            "stance": "supports",
            "raw_predicate": "identifies",
        },
    },
    {
        "ref": "Claim:claim-47b3f70bc68cb2597798",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "canonical_relation": "is_avoided_by",
            "confidence": 0.9,
            "id": "claim-47b3f70bc68cb2597798",
            "text": "Rinsing the can immediately after use prevents leftover sugary beverage residue from interfering "
            "with the project.",
            "stance": "supports",
            "raw_predicate": "is avoided by",
        },
    },
    {
        "ref": "Claim:claim-4f0858a9aba66b1f6d4a",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.821000000+00:00",
            "canonical_relation": "has",
            "confidence": 0.9,
            "id": "claim-4f0858a9aba66b1f6d4a",
            "text": "Skipped on purpose: decorative storage boxes I did not truly need.",
            "stance": "supports",
            "raw_predicate": "avoids purchasing",
        },
    },
    {
        "ref": "Claim:claim-5c74eba56a0c56188b1d",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.483000000+00:00",
            "canonical_relation": "is_recommended_for_storing",
            "confidence": 0.9,
            "id": "claim-5c74eba56a0c56188b1d",
            "text": "If you are decorating for National Day and want something quick, affordable, and easy to "
            "photograph, this one is really worth trying.",
            "stance": "supports",
            "raw_predicate": "recommended for",
        },
    },
    {
        "ref": "Claim:claim-5e6073daa8cc48e3e0d3",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "canonical_relation": "enhances",
            "confidence": 0.8,
            "id": "claim-5e6073daa8cc48e3e0d3",
            "text": "Constructing two identical holders at once yields a more cohesive and put-together display on a "
            "shelf or desk compared to a single unit.",
            "stance": "supports",
            "raw_predicate": "enhances",
        },
    },
    {
        "ref": "Claim:claim-5e8843f752deb6ad8146",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "canonical_relation": "enables",
            "confidence": 0.8,
            "id": "claim-5e8843f752deb6ad8146",
            "text": "Visible, uniform labels allow the user to quickly see available supplies and manage stock "
            "effectively.",
            "stance": "supports",
            "raw_predicate": "enables",
        },
    },
    {
        "ref": "Claim:claim-62c8a6f9cd2d046364a1",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "canonical_relation": "decorated_with",
            "confidence": 0.9,
            "id": "claim-62c8a6f9cd2d046364a1",
            "text": "A simple ribbon and one small dried flower tag were added to finish the presentation.",
            "stance": "supports",
            "raw_predicate": "decorated with",
        },
    },
    {
        "ref": "Claim:claim-65ce9039b9a8f38b163c",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.713000000+00:00",
            "canonical_relation": "provide_instructions_for",
            "confidence": 0.8,
            "id": "claim-65ce9039b9a8f38b163c",
            "text": "Placing a rinse reminder above the plastic bin ensures containers are washed before disposal.",
            "stance": "supports",
            "raw_predicate": "provide instructions for",
        },
    },
    {
        "ref": "Claim:claim-6b956deae93fd003d888",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.643000000+00:00",
            "canonical_relation": "is_recommended_for_storing",
            "confidence": 0.85,
            "id": "claim-6b956deae93fd003d888",
            "text": "The DIY organizer effectively collects loose pens, scissors, or charging cables that typically "
            "clutter a desk.",
            "stance": "supports",
            "raw_predicate": "is recommended for storing",
        },
    },
    {
        "ref": "Claim:claim-6bff894449c8627cbe60",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "canonical_relation": "should_segregate",
            "confidence": 0.85,
            "id": "claim-6bff894449c8627cbe60",
            "text": "Use a dedicated small box for AA and AAA batteries while isolating button batteries in a separate "
            "pouch.",
            "stance": "supports",
            "raw_predicate": "should segregate",
        },
    },
    {
        "ref": "Claim:claim-6d00d6c480959ccb58b3",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.833000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "confidence": 0.85,
            "id": "claim-6d00d6c480959ccb58b3",
            "text": "Fully covering the exterior with paper gives the recycled can a deliberately designed appearance "
            "rather than looking discarded.",
            "stance": "supports",
            "raw_predicate": "provides",
        },
    },
    {
        "ref": "Claim:claim-6f2283ac450218475788",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.542000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.95,
            "id": "claim-6f2283ac450218475788",
            "text": "the power bank definitely belongs in proper recycling.",
            "stance": "supports",
            "raw_predicate": "requires",
        },
    },
    {
        "ref": "Claim:claim-70a1d717e109eeb320cd",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.241000000+00:00",
            "canonical_relation": "filters",
            "confidence": 0.8,
            "id": "claim-70a1d717e109eeb320cd",
            "text": "The approach quickly reveals whether an item is actually needed or just an impulse purchase.",
            "stance": "supports",
            "raw_predicate": "filters",
        },
    },
    {
        "ref": "Claim:claim-76f621a289570d6ce85b",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "canonical_relation": "eliminates_concern_about",
            "confidence": 0.8,
            "id": "claim-76f621a289570d6ce85b",
            "text": "Cleaning and reusing previously kept jam jars resolved the personal guilt associated with "
            "throwing away leftover packaging.",
            "stance": "supports",
            "raw_predicate": "eliminates_concern_about",
        },
    },
    {
        "ref": "Claim:claim-7e2b31ffe495f7f8b6a9",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.207000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "confidence": 0.9,
            "id": "claim-7e2b31ffe495f7f8b6a9",
            "text": "Converting an existing tin provided necessary storage without requiring the acquisition of a new "
            "kitchen container.",
            "stance": "supports",
            "raw_predicate": "replaces purchase of",
        },
    },
    {
        "ref": "Claim:claim-81392ac5c162628330f5",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.988000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "confidence": 0.85,
            "id": "claim-81392ac5c162628330f5",
            "text": "Chose to reuse jars and trays I already had instead of buying new storage.",
            "stance": "supports",
            "raw_predicate": "repurposes",
        },
    },
    {
        "ref": "Claim:claim-87a159d48e1d517cd860",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.894000000+00:00",
            "canonical_relation": "compatible_with",
            "confidence": 0.8,
            "id": "claim-87a159d48e1d517cd860",
            "text": "Remote controls were selected as one of the first high-use devices to adopt rechargeable "
            "batteries.",
            "stance": "supports",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Claim:claim-8bd2c561fc2a5133e0fb",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "canonical_relation": "secured_with",
            "confidence": 0.85,
            "id": "claim-8bd2c561fc2a5133e0fb",
            "text": "Double-sided tape was used to firmly attach the kraft paper wrapping.",
            "stance": "supports",
            "raw_predicate": "secured with",
        },
    },
    {
        "ref": "Claim:claim-8e0b0340a06f59c90afd",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.394000000+00:00",
            "canonical_relation": "minimizes",
            "confidence": 0.85,
            "id": "claim-8e0b0340a06f59c90afd",
            "text": "Using one style of label on the jars makes inventory visible, reducing the likelihood of "
            "repurchasing duplicates.",
            "stance": "supports",
            "raw_predicate": "minimizes",
        },
    },
    {
        "ref": "Claim:claim-90ce1e24293c3efc26db",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.632000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "confidence": 0.85,
            "id": "claim-90ce1e24293c3efc26db",
            "text": "Repurposing stored mailers eliminates the recurring need to purchase new boxes for small gifts.",
            "stance": "supports",
            "raw_predicate": "replaces",
        },
    },
    {
        "ref": "Claim:claim-99897f9a68a6949b1d02",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.792000000+00:00",
            "canonical_relation": "scheduled_for",
            "confidence": 0.9,
            "id": "claim-99897f9a68a6949b1d02",
            "text": "The organizer proposes a low-pressure one-hour reset beginning at 9:00 AM on Saturday.",
            "stance": "supports",
            "raw_predicate": "scheduled_for",
        },
    },
    {
        "ref": "Claim:claim-9cc49078709c0bbe83b2",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.001000000+00:00",
            "canonical_relation": "applied_to_exterior_of",
            "confidence": 0.9,
            "id": "claim-9cc49078709c0bbe83b2",
            "text": "A wrap of linen-texture adhesive paper was added to the tin to improve its aesthetic appeal on "
            "the counter.",
            "stance": "supports",
            "raw_predicate": "applied to exterior of",
        },
    },
    {
        "ref": "Claim:claim-9d83516342e2cd07ddad",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.286000000+00:00",
            "canonical_relation": "repurposed_for",
            "confidence": 0.9,
            "id": "claim-9d83516342e2cd07ddad",
            "text": "Old glass jars were cleaned and reused to organize a spice shelf, resulting in a more cohesive "
            "appearance.",
            "stance": "supports",
            "raw_predicate": "repurposed_for",
        },
    },
    {
        "ref": "Claim:claim-a125183d312510a757a0",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.628000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.9,
            "id": "claim-a125183d312510a757a0",
            "text": "Vague bin setups lead to mistakes, but clear labels with words and colors make proper sorting "
            "obvious.",
            "stance": "supports",
            "raw_predicate": "require",
        },
    },
    {
        "ref": "Claim:claim-a4986a2367d0ed03a459",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "canonical_relation": "improve",
            "confidence": 0.85,
            "id": "claim-a4986a2367d0ed03a459",
            "text": "Reorganizing the spice shelf with matching jars changed the overall feeling of the kitchen, "
            "making it appear calmer.",
            "stance": "supports",
            "raw_predicate": "improves_ambiance_of",
        },
    },
    {
        "ref": "Claim:claim-a4dc373bbb84547ffb39",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.235000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.85,
            "id": "claim-a4dc373bbb84547ffb39",
            "text": "Tape the terminals on rechargeable batteries to prevent shorting during the sorting process.",
            "stance": "supports",
            "raw_predicate": "require terminal protection",
        },
    },
    {
        "ref": "Claim:claim-bbf72e6e54ed216fa4ea",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "confidence": 0.9,
            "id": "claim-bbf72e6e54ed216fa4ea",
            "text": "Gloves, spare bags, and sorting labels are provided to ensure a practical clean-and-go session.",
            "stance": "supports",
            "raw_predicate": "provides",
        },
    },
    {
        "ref": "Claim:claim-c17e04775274afbca44d",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.431000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "confidence": 0.95,
            "id": "claim-c17e04775274afbca44d",
            "text": "I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and used them to "
            "separate drawer contents.",
            "stance": "supports",
            "raw_predicate": "repurposed as",
        },
    },
    {
        "ref": "Claim:claim-c41c7cd06aee83d56291",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.504000000+00:00",
            "canonical_relation": "reduces_visual_clutter_in",
            "confidence": 0.9,
            "id": "claim-c41c7cd06aee83d56291",
            "text": "The brown paper also made the drawer feel visually calmer compared to a mix of loose plastic "
            "packaging.",
            "stance": "supports",
            "raw_predicate": "reduces visual clutter in",
        },
    },
    {
        "ref": "Claim:claim-c798880471301f0b2423",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:24.064000000+00:00",
            "canonical_relation": "compatible_with",
            "confidence": 0.8,
            "id": "claim-c798880471301f0b2423",
            "text": "A frequently used wireless mouse was included in the initial devices transitioned to rechargeable "
            "batteries.",
            "stance": "supports",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Claim:claim-dac139e1590581f31d92",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "canonical_relation": "tolerates",
            "confidence": 0.85,
            "id": "claim-dac139e1590581f31d92",
            "text": "The process requires no perfection, as slightly uneven folds still produce a warm and personal "
            "result.",
            "stance": "supports",
            "raw_predicate": "tolerates",
        },
    },
    {
        "ref": "Claim:claim-dc2a9817d735b152e991",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.892000000+00:00",
            "canonical_relation": "rejects",
            "confidence": 0.85,
            "id": "claim-dc2a9817d735b152e991",
            "text": "Trendy acrylic organizers looked nice but solved no real problem.",
            "stance": "warns",
            "raw_predicate": "rejects",
        },
    },
    {
        "ref": "Claim:claim-dfb94e8f4a04968e9efe",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.633000000+00:00",
            "canonical_relation": "has",
            "confidence": 0.85,
            "id": "claim-dfb94e8f4a04968e9efe",
            "text": "The paper sleeve would probably not survive forever under continuous use.",
            "stance": "warns",
            "raw_predicate": "has limited longevity in",
        },
    },
    {
        "ref": "Claim:claim-e1839e9b577645272c10",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.256000000+00:00",
            "canonical_relation": "borrows",
            "confidence": 0.9,
            "id": "claim-e1839e9b577645272c10",
            "text": "Opted to borrow essential items like a desk lamp rather than buying new ones.",
            "stance": "supports",
            "raw_predicate": "borrows",
        },
    },
    {
        "ref": "Claim:claim-e9fc06beb86a8df34bbd",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.643000000+00:00",
            "canonical_relation": "reduce_friction_in",
            "confidence": 0.85,
            "id": "claim-e9fc06beb86a8df34bbd",
            "text": "Implementing a clear system reduced annoying cleanup conversations about where items belong after "
            "dinner.",
            "stance": "supports",
            "raw_predicate": "reduce friction in",
        },
    },
    {
        "ref": "Claim:claim-ea09ed210b63909cab62",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.619000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "confidence": 0.9,
            "id": "claim-ea09ed210b63909cab62",
            "text": "A clean aluminum can can be transformed into a functional desk cup by sanding, wrapping, and "
            "adding a label.",
            "stance": "supports",
            "raw_predicate": "can be converted into",
        },
    },
    {
        "ref": "Claim:claim-eb9462ee5e425ecd086e",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "canonical_relation": "should_be_evaluated_for",
            "confidence": 0.85,
            "id": "claim-eb9462ee5e425ecd086e",
            "text": "Verify whether batteries are completely dead or still actively needed by devices before "
            "discarding them.",
            "stance": "supports",
            "raw_predicate": "should be evaluated for",
        },
    },
    {
        "ref": "Claim:claim-f2a898b934440d547efd",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.883000000+00:00",
            "canonical_relation": "reduces_visual_clutter_in",
            "confidence": 0.85,
            "id": "claim-f2a898b934440d547efd",
            "text": "Switching to rechargeable batteries immediately reduces loose batteries in drawers and decreases "
            "overall battery waste.",
            "stance": "supports",
            "raw_predicate": "reduce",
        },
    },
    {
        "ref": "Claim:claim-f36072afe90ff168ad03",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.747000000+00:00",
            "canonical_relation": "require",
            "confidence": 0.9,
            "id": "claim-f36072afe90ff168ad03",
            "text": "Properly smoothing the sharp aluminum edge is necessary to ensure the finished holder feels safe "
            "to handle.",
            "stance": "supports",
            "raw_predicate": "requires",
        },
    },
    {
        "ref": "Claim:claim-f92e492ce435f8626de6",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.113000000+00:00",
            "canonical_relation": "selects",
            "confidence": 0.85,
            "id": "claim-f92e492ce435f8626de6",
            "text": "Selected one sturdy tote alongside a single laundry basket for practical storage.",
            "stance": "supports",
            "raw_predicate": "selects",
        },
    },
    {
        "ref": "Claim:claim-f9fc4f597a1d720cd385",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.423000000+00:00",
            "canonical_relation": "accumulates",
            "confidence": 0.9,
            "id": "claim-f9fc4f597a1d720cd385",
            "text": "I spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned.",
            "stance": "supports",
            "raw_predicate": "accumulates",
        },
    },
    {
        "ref": "Claim:claim-fd1508f2a092951630dc",
        "labels": ["Claim"],
        "props": {
            "updated_at": "2026-05-12T13:15:17.906000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "confidence": 0.95,
            "id": "claim-fd1508f2a092951630dc",
            "text": "An empty metal coffee tin was cleaned and transformed into a functional utensil holder for daily "
            "use.",
            "stance": "supports",
            "raw_predicate": "repurposed as",
        },
    },
    {
        "ref": "Entity:aa_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "normalized_name": "aa_batteries",
            "display_name": "AA batteries",
        },
    },
    {
        "ref": "Entity:aaa_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:20:25.991000000+00:00",
            "normalized_name": "aaa_batteries",
            "display_name": "AAA batteries",
        },
    },
    {
        "ref": "Entity:acrylic_organizers",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:56.892000000+00:00",
            "normalized_name": "acrylic_organizers",
            "display_name": "acrylic organizers",
        },
    },
    {
        "ref": "Entity:adhesive_paper",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:18.001000000+00:00",
            "normalized_name": "adhesive_paper",
            "display_name": "adhesive paper",
        },
    },
    {
        "ref": "Entity:aluminum_can",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.619000000+00:00",
            "normalized_name": "aluminum_can",
            "display_name": "Aluminum can",
        },
    },
    {
        "ref": "Entity:battery_recycling",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "normalized_name": "battery_recycling",
            "display_name": "battery recycling",
        },
    },
    {
        "ref": "Entity:battery_waste",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:23.883000000+00:00",
            "normalized_name": "battery_waste",
            "display_name": "battery waste",
        },
    },
    {
        "ref": "Entity:button_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:20:25.991000000+00:00",
            "normalized_name": "button_batteries",
            "display_name": "button batteries",
        },
    },
    {
        "ref": "Entity:cardboard_mailer",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.581000000+00:00",
            "normalized_name": "cardboard_mailer",
            "display_name": "cardboard mailer",
        },
    },
    {
        "ref": "Entity:category_check",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "normalized_name": "category_check",
            "display_name": "category check",
        },
    },
    {
        "ref": "Entity:cleaning",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "normalized_name": "cleaning",
            "display_name": "cleaning",
        },
    },
    {
        "ref": "Entity:cleaning_supplies",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "normalized_name": "cleaning_supplies",
            "display_name": "Cleaning supplies",
        },
    },
    {
        "ref": "Entity:cleanup_session",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "normalized_name": "cleanup_session",
            "display_name": "Cleanup session",
        },
    },
    {
        "ref": "Entity:coffee_tin",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:18.207000000+00:00",
            "normalized_name": "coffee_tin",
            "display_name": "coffee tin",
        },
    },
    {
        "ref": "Entity:commercial_organizer",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "normalized_name": "commercial_organizer",
            "display_name": "Commercial organizer",
        },
    },
    {
        "ref": "Entity:consistent_labeling",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "normalized_name": "consistent_labeling",
            "display_name": "consistent labeling",
        },
    },
    {
        "ref": "Entity:cooking_utensils",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:15:17.866000000+00:00",
            "normalized_name": "cooking_utensils",
            "display_name": "cooking utensils",
        },
    },
    {
        "ref": "Entity:cut_edge",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.747000000+00:00",
            "normalized_name": "cut_edge",
            "display_name": "Cut edge",
        },
    },
    {
        "ref": "Entity:decorative_storage_boxes",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:56.821000000+00:00",
            "normalized_name": "decorative_storage_boxes",
            "display_name": "decorative storage boxes",
        },
    },
    {
        "ref": "Entity:desk",
        "labels": ["Entity"],
        "props": {
            "entity_type": "place",
            "updated_at": "2026-05-12T13:18:19.566000000+00:00",
            "normalized_name": "desk",
            "display_name": "Desk",
        },
    },
    {
        "ref": "Entity:desk_drawer",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.423000000+00:00",
            "normalized_name": "desk_drawer",
            "display_name": "desk drawer",
        },
    },
    {
        "ref": "Entity:desk_lamp",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.256000000+00:00",
            "normalized_name": "desk_lamp",
            "display_name": "desk lamp",
        },
    },
    {
        "ref": "Entity:digital_notes",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "normalized_name": "digital_notes",
            "display_name": "digital notes",
        },
    },
    {
        "ref": "Entity:disposable_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:23.812000000+00:00",
            "normalized_name": "disposable_batteries",
            "display_name": "disposable batteries",
        },
    },
    {
        "ref": "Entity:disposal_options",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "normalized_name": "disposal_options",
            "display_name": "disposal options",
        },
    },
    {
        "ref": "Entity:diy_lantern",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "normalized_name": "diy_lantern",
            "display_name": "DIY lantern",
        },
    },
    {
        "ref": "Entity:dorm_room",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.274000000+00:00",
            "normalized_name": "dorm_room",
            "display_name": "dorm room",
        },
    },
    {
        "ref": "Entity:double_sided_tape",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "normalized_name": "double_sided_tape",
            "display_name": "double-sided tape",
        },
    },
    {
        "ref": "Entity:drawer_divider",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.633000000+00:00",
            "normalized_name": "drawer_divider",
            "display_name": "Drawer divider",
        },
    },
    {
        "ref": "Entity:dried_flower_tag",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:18:54.439000000+00:00",
            "normalized_name": "dried_flower_tag",
            "display_name": "dried flower tag",
        },
    },
    {
        "ref": "Entity:drop_off",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "normalized_name": "drop_off",
            "display_name": "drop-off",
        },
    },
    {
        "ref": "Entity:drop_off_locations",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "normalized_name": "drop_off_locations",
            "display_name": "drop-off locations",
        },
    },
    {
        "ref": "Entity:duplicate_purchases",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.394000000+00:00",
            "normalized_name": "duplicate_purchases",
            "display_name": "duplicate purchases",
        },
    },
    {
        "ref": "Entity:e_waste",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "normalized_name": "e_waste",
            "display_name": "e-waste",
        },
    },
    {
        "ref": "Entity:electrical_tape",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.235000000+00:00",
            "normalized_name": "electrical_tape",
            "display_name": "electrical tape",
        },
    },
    {
        "ref": "Entity:festive_craft_reuse",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "normalized_name": "festive_craft_reuse",
            "display_name": "festive craft reuse",
        },
    },
    {
        "ref": "Entity:flashlight",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:23.991000000+00:00",
            "normalized_name": "flashlight",
            "display_name": "flashlight",
        },
    },
    {
        "ref": "Entity:gift_box",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "normalized_name": "gift_box",
            "display_name": "gift box",
        },
    },
    {
        "ref": "Entity:glass_jars",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "normalized_name": "glass_jars",
            "display_name": "glass jars",
        },
    },
    {
        "ref": "Entity:handmade_appearance",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "normalized_name": "handmade_appearance",
            "display_name": "handmade appearance",
        },
    },
    {
        "ref": "Entity:household_recycling",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "normalized_name": "household_recycling",
            "display_name": "household recycling",
        },
    },
    {
        "ref": "Entity:immediate_washing",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "normalized_name": "immediate_washing",
            "display_name": "Immediate washing",
        },
    },
    {
        "ref": "Entity:imperfect_execution",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "normalized_name": "imperfect_execution",
            "display_name": "imperfect execution",
        },
    },
    {
        "ref": "Entity:impulse_purchases",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.241000000+00:00",
            "normalized_name": "impulse_purchases",
            "display_name": "impulse purchases",
        },
    },
    {
        "ref": "Entity:intentional_aesthetic",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.833000000+00:00",
            "normalized_name": "intentional_aesthetic",
            "display_name": "Intentional aesthetic",
        },
    },
    {
        "ref": "Entity:inventory_tracking",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "normalized_name": "inventory_tracking",
            "display_name": "inventory tracking",
        },
    },
    {
        "ref": "Entity:jars",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:56.988000000+00:00",
            "normalized_name": "jars",
            "display_name": "jars",
        },
    },
    {
        "ref": "Entity:keyboard",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "normalized_name": "keyboard",
            "display_name": "keyboard",
        },
    },
    {
        "ref": "Entity:kitchen",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "normalized_name": "kitchen",
            "display_name": "kitchen",
        },
    },
    {
        "ref": "Entity:kitchen_containers",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:18.207000000+00:00",
            "normalized_name": "kitchen_containers",
            "display_name": "kitchen containers",
        },
    },
    {
        "ref": "Entity:kitchen_countertop",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "normalized_name": "kitchen_countertop",
            "display_name": "kitchen countertop",
        },
    },
    {
        "ref": "Entity:kitchen_drawer",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.574000000+00:00",
            "normalized_name": "kitchen_drawer",
            "display_name": "Kitchen drawer",
        },
    },
    {
        "ref": "Entity:kraft_paper",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "normalized_name": "kraft_paper",
            "display_name": "kraft paper",
        },
    },
    {
        "ref": "Entity:laundry_basket",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:16:56.777000000+00:00",
            "normalized_name": "laundry_basket",
            "display_name": "laundry basket",
        },
    },
    {
        "ref": "Entity:led_light",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.494000000+00:00",
            "normalized_name": "led_light",
            "display_name": "LED light",
        },
    },
    {
        "ref": "Entity:lithium_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.133000000+00:00",
            "normalized_name": "lithium_batteries",
            "display_name": "lithium batteries",
        },
    },
    {
        "ref": "Entity:litter",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "normalized_name": "litter",
            "display_name": "Litter",
        },
    },
    {
        "ref": "Entity:long_term_storage",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.633000000+00:00",
            "normalized_name": "long_term_storage",
            "display_name": "Long-term storage",
        },
    },
    {
        "ref": "Entity:loose_stationery",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.643000000+00:00",
            "normalized_name": "loose_stationery",
            "display_name": "Loose stationery",
        },
    },
    {
        "ref": "Entity:low_buy_approach",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.274000000+00:00",
            "normalized_name": "low_buy_approach",
            "display_name": "low-buy approach",
        },
    },
    {
        "ref": "Entity:matching_pair",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "normalized_name": "matching_pair",
            "display_name": "Matching pair",
        },
    },
    {
        "ref": "Entity:national_day",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.483000000+00:00",
            "normalized_name": "national_day",
            "display_name": "National Day",
        },
    },
    {
        "ref": "Entity:new_packaging",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.632000000+00:00",
            "normalized_name": "new_packaging",
            "display_name": "new packaging",
        },
    },
    {
        "ref": "Entity:non_waste_items",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "normalized_name": "non_waste_items",
            "display_name": "non-waste items",
        },
    },
    {
        "ref": "Entity:packaging_waste",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "normalized_name": "packaging_waste",
            "display_name": "packaging waste",
        },
    },
    {
        "ref": "Entity:paper_bag",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.431000000+00:00",
            "normalized_name": "paper_bag",
            "display_name": "Paper bag",
        },
    },
    {
        "ref": "Entity:paper_wrap",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.833000000+00:00",
            "normalized_name": "paper_wrap",
            "display_name": "Paper wrap",
        },
    },
    {
        "ref": "Entity:pen_holder",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.643000000+00:00",
            "normalized_name": "pen_holder",
            "display_name": "Pen holder",
        },
    },
    {
        "ref": "Entity:plastic_bottle",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "normalized_name": "plastic_bottle",
            "display_name": "plastic bottle",
        },
    },
    {
        "ref": "Entity:power_bank",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.542000000+00:00",
            "normalized_name": "power_bank",
            "display_name": "power bank",
        },
    },
    {
        "ref": "Entity:pre_sorted_organization",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "normalized_name": "pre_sorted_organization",
            "display_name": "pre-sorted organization",
        },
    },
    {
        "ref": "Entity:rechargeable_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.235000000+00:00",
            "normalized_name": "rechargeable_batteries",
            "display_name": "rechargeable batteries",
        },
    },
    {
        "ref": "Entity:recyclables",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.864000000+00:00",
            "normalized_name": "recyclables",
            "display_name": "Recyclables",
        },
    },
    {
        "ref": "Entity:recycling_bins",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "normalized_name": "recycling_bins",
            "display_name": "recycling bins",
        },
    },
    {
        "ref": "Entity:remaining_functionality",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "normalized_name": "remaining_functionality",
            "display_name": "remaining functionality",
        },
    },
    {
        "ref": "Entity:remote_controls",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:23.894000000+00:00",
            "normalized_name": "remote_controls",
            "display_name": "remote controls",
        },
    },
    {
        "ref": "Entity:responsible_recycling",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.542000000+00:00",
            "normalized_name": "responsible_recycling",
            "display_name": "responsible recycling",
        },
    },
    {
        "ref": "Entity:ribbon",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "normalized_name": "ribbon",
            "display_name": "ribbon",
        },
    },
    {
        "ref": "Entity:riverside_path",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "normalized_name": "riverside_path",
            "display_name": "Riverside path",
        },
    },
    {
        "ref": "Entity:sanding",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.747000000+00:00",
            "normalized_name": "sanding",
            "display_name": "Sanding",
        },
    },
    {
        "ref": "Entity:saturday",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:49.792000000+00:00",
            "normalized_name": "saturday",
            "display_name": "Saturday",
        },
    },
    {
        "ref": "Entity:sorting_labels",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:17:31.713000000+00:00",
            "normalized_name": "sorting_labels",
            "display_name": "sorting labels",
        },
    },
    {
        "ref": "Entity:spice_shelf",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "normalized_name": "spice_shelf",
            "display_name": "spice shelf",
        },
    },
    {
        "ref": "Entity:sticky_residue",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "normalized_name": "sticky_residue",
            "display_name": "Sticky residue",
        },
    },
    {
        "ref": "Entity:storage_containers",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "normalized_name": "storage_containers",
            "display_name": "storage containers",
        },
    },
    {
        "ref": "Entity:surfaces",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.129000000+00:00",
            "normalized_name": "surfaces",
            "display_name": "surfaces",
        },
    },
    {
        "ref": "Entity:tech_drawer_reset",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "normalized_name": "tech_drawer_reset",
            "display_name": "tech drawer reset",
        },
    },
    {
        "ref": "Entity:tote",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:57.113000000+00:00",
            "normalized_name": "tote",
            "display_name": "tote",
        },
    },
    {
        "ref": "Entity:trays",
        "labels": ["Entity"],
        "props": {
            "entity_type": "item",
            "updated_at": "2026-05-12T13:16:56.777000000+00:00",
            "normalized_name": "trays",
            "display_name": "trays",
        },
    },
    {
        "ref": "Entity:upcycling",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "normalized_name": "upcycling",
            "display_name": "upcycling",
        },
    },
    {
        "ref": "Entity:used_batteries",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "normalized_name": "used_batteries",
            "display_name": "used batteries",
        },
    },
    {
        "ref": "Entity:utensil_holder",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "normalized_name": "utensil_holder",
            "display_name": "utensil holder",
        },
    },
    {
        "ref": "Entity:visual_balance",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "normalized_name": "visual_balance",
            "display_name": "Visual balance",
        },
    },
    {
        "ref": "Entity:wireless_mouse",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:16:24.064000000+00:00",
            "normalized_name": "wireless_mouse",
            "display_name": "wireless mouse",
        },
    },
    {
        "ref": "Entity:zero_cost_hack",
        "labels": ["Entity"],
        "props": {
            "entity_type": "concept",
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "normalized_name": "zero_cost_hack",
            "display_name": "Zero-cost hack",
        },
    },
    {
        "ref": "Evidence:evidence-1226d293c719a0d201cc",
        "labels": ["Evidence"],
        "props": {
            "post_id": 9,
            "updated_at": "2026-05-12T13:15:53.633000000+00:00",
            "canonical_relation": "has",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-1226d293c719a0d201cc",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "excerpt": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer I needed quick "
            "drawer dividers and really did not want to buy a whole organizer set for one messy kitchen "
            "drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and "
            "used them to separate clips, tea sachets, a",
            "chunk_id": "post-9-v2-c0",
            "url": "/forum/posts/9",
            "raw_predicate": "has limited longevity in",
        },
    },
    {
        "ref": "Evidence:evidence-13a05c17a49eba877729",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:57.129000000+00:00",
            "canonical_relation": "keeps_clear",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-13a05c17a49eba877729",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "keeps clear",
        },
    },
    {
        "ref": "Evidence:evidence-165347d7d10023a84336",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:56.821000000+00:00",
            "canonical_relation": "has",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-165347d7d10023a84336",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "avoids purchasing",
        },
    },
    {
        "ref": "Evidence:evidence-16aa4be77f122010ce74",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "canonical_relation": "should_be_evaluated_for",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-16aa4be77f122010ce74",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "should be evaluated for",
        },
    },
    {
        "ref": "Evidence:evidence-1882f0b12bab2f949fd5",
        "labels": ["Evidence"],
        "props": {
            "post_id": 7,
            "updated_at": "2026-05-12T13:19:32.394000000+00:00",
            "canonical_relation": "minimizes",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-1882f0b12bab2f949fd5",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "excerpt": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨ "
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, "
            "and used them to reorganize my spice sh",
            "chunk_id": "post-7-v2-c0",
            "url": "/forum/posts/7",
            "raw_predicate": "minimizes",
        },
    },
    {
        "ref": "Evidence:evidence-1af11d29eee64d056dcb",
        "labels": ["Evidence"],
        "props": {
            "post_id": 7,
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "canonical_relation": "enables",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-1af11d29eee64d056dcb",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "excerpt": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨ "
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, "
            "and used them to reorganize my spice sh",
            "chunk_id": "post-7-v2-c0",
            "url": "/forum/posts/7",
            "raw_predicate": "enables",
        },
    },
    {
        "ref": "Evidence:evidence-1ca4ec35064bacf013cb",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "canonical_relation": "enhances",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-1ca4ec35064bacf013cb",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "enhances",
        },
    },
    {
        "ref": "Evidence:evidence-1f7a5871d1852c509a43",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "canonical_relation": "tolerates",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-1f7a5871d1852c509a43",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "tolerates",
        },
    },
    {
        "ref": "Evidence:evidence-22cce2e85458548451f1",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.542000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.95,
            "active": True,
            "id": "evidence-22cce2e85458548451f1",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "requires",
        },
    },
    {
        "ref": "Evidence:evidence-283049beb78a0fd66db7",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:56.988000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-283049beb78a0fd66db7",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "repurposes",
        },
    },
    {
        "ref": "Evidence:evidence-29af1598dd49db086af0",
        "labels": ["Evidence"],
        "props": {
            "post_id": 11,
            "updated_at": "2026-05-12T13:16:23.894000000+00:00",
            "canonical_relation": "compatible_with",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-29af1598dd49db086af0",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "excerpt": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋 I finally "
            "replaced the constant stream of disposable batteries in a few small household devices with "
            "rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mo",
            "chunk_id": "post-11-v2-c0",
            "url": "/forum/posts/11",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Evidence:evidence-2b5441320dd432a89bc7",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:57.274000000+00:00",
            "canonical_relation": "enhances",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-2b5441320dd432a89bc7",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "enhances",
        },
    },
    {
        "ref": "Evidence:evidence-2d032b2634b46e067677",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.423000000+00:00",
            "canonical_relation": "accumulates",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-2d032b2634b46e067677",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "accumulates",
        },
    },
    {
        "ref": "Evidence:evidence-2da743881c28da58a96e",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "canonical_relation": "should_segregate",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-2da743881c28da58a96e",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "should segregate",
        },
    },
    {
        "ref": "Evidence:evidence-2fb7462b5de5605a8d90",
        "labels": ["Evidence"],
        "props": {
            "post_id": 5,
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-2fb7462b5de5605a8d90",
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "excerpt": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together? I "
            "walked by the riverside path again this morning and noticed the same pattern as last week: "
            "plastic bottles near the benches, snack wrappers caught in the grass, and a surprising number "
            "of cans around the bike parking area. So",
            "chunk_id": "post-5-v2-c0",
            "url": "/forum/posts/5",
            "raw_predicate": "provides",
        },
    },
    {
        "ref": "Evidence:evidence-304601b6d02f13d2594b",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:56.892000000+00:00",
            "canonical_relation": "rejects",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-304601b6d02f13d2594b",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "rejects",
        },
    },
    {
        "ref": "Evidence:evidence-32b77ba1680f8757199e",
        "labels": ["Evidence"],
        "props": {
            "post_id": 7,
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "canonical_relation": "eliminates_concern_about",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-32b77ba1680f8757199e",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "excerpt": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨ "
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, "
            "and used them to reorganize my spice sh",
            "chunk_id": "post-7-v2-c0",
            "url": "/forum/posts/7",
            "raw_predicate": "eliminates_concern_about",
        },
    },
    {
        "ref": "Evidence:evidence-3a4df5b0e29e1b55f56a",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "canonical_relation": "is_avoided_by",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-3a4df5b0e29e1b55f56a",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "is avoided by",
        },
    },
    {
        "ref": "Evidence:evidence-3b12e45bda1ce087ba77",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:57.241000000+00:00",
            "canonical_relation": "filters",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-3b12e45bda1ce087ba77",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "filters",
        },
    },
    {
        "ref": "Evidence:evidence-40e48eb38a6259af85ef",
        "labels": ["Evidence"],
        "props": {
            "post_id": 12,
            "updated_at": "2026-05-12T13:17:31.628000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-40e48eb38a6259af85ef",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "excerpt": "The home sorting labels that finally made my family recycle properly ♻️🏷️ I used to explain "
            "the same thing every week: which bin was for paper, which one was for plastic, and why rinsing "
            "containers mattered. Nobody meant to do it wrong, but our setup was too vague. This week I "
            "made simple printed labels for each bin, a",
            "chunk_id": "post-12-v2-c0",
            "url": "/forum/posts/12",
            "raw_predicate": "require",
        },
    },
    {
        "ref": "Evidence:evidence-4595106c82cde7df0cac",
        "labels": ["Evidence"],
        "props": {
            "post_id": 12,
            "updated_at": "2026-05-12T13:17:31.612000000+00:00",
            "canonical_relation": "improve",
            "extraction_confidence": 0.95,
            "active": True,
            "id": "evidence-4595106c82cde7df0cac",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "excerpt": "The home sorting labels that finally made my family recycle properly ♻️🏷️ I used to explain "
            "the same thing every week: which bin was for paper, which one was for plastic, and why rinsing "
            "containers mattered. Nobody meant to do it wrong, but our setup was too vague. This week I "
            "made simple printed labels for each bin, a",
            "chunk_id": "post-12-v2-c0",
            "url": "/forum/posts/12",
            "raw_predicate": "improve",
        },
    },
    {
        "ref": "Evidence:evidence-482695c5d2b311cadb77",
        "labels": ["Evidence"],
        "props": {
            "post_id": 11,
            "updated_at": "2026-05-12T13:16:24.064000000+00:00",
            "canonical_relation": "compatible_with",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-482695c5d2b311cadb77",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "excerpt": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋 I finally "
            "replaced the constant stream of disposable batteries in a few small household devices with "
            "rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mo",
            "chunk_id": "post-11-v2-c0",
            "url": "/forum/posts/11",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Evidence:evidence-4f3d3ad6ec29f1103bba",
        "labels": ["Evidence"],
        "props": {
            "post_id": 4,
            "updated_at": "2026-05-12T13:15:18.001000000+00:00",
            "canonical_relation": "applied_to_exterior_of",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-4f3d3ad6ec29f1103bba",
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "excerpt": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades I "
            "cleaned out an empty metal coffee tin this week and turned it into a countertop utensil "
            "holder. It was one of those projects that took almost no time but made the kitchen feel much "
            "more settled. What I did: - washed and dried the t",
            "chunk_id": "post-4-v3-c0",
            "url": "/forum/posts/4",
            "raw_predicate": "applied to exterior of",
        },
    },
    {
        "ref": "Evidence:evidence-507e77e6876017b80d99",
        "labels": ["Evidence"],
        "props": {
            "post_id": 7,
            "updated_at": "2026-05-12T13:19:32.286000000+00:00",
            "canonical_relation": "repurposed_for",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-507e77e6876017b80d99",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "excerpt": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨ "
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, "
            "and used them to reorganize my spice sh",
            "chunk_id": "post-7-v2-c0",
            "url": "/forum/posts/7",
            "raw_predicate": "repurposed_for",
        },
    },
    {
        "ref": "Evidence:evidence-57cded6e886f40df3aee",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:57.256000000+00:00",
            "canonical_relation": "borrows",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-57cded6e886f40df3aee",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "borrows",
        },
    },
    {
        "ref": "Evidence:evidence-5b62461dd01fe92249b4",
        "labels": ["Evidence"],
        "props": {
            "post_id": 11,
            "updated_at": "2026-05-12T13:16:23.812000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-5b62461dd01fe92249b4",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "excerpt": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋 I finally "
            "replaced the constant stream of disposable batteries in a few small household devices with "
            "rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mo",
            "chunk_id": "post-11-v2-c0",
            "url": "/forum/posts/11",
            "raw_predicate": "replace",
        },
    },
    {
        "ref": "Evidence:evidence-5dee65001425be0b1998",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.483000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-5dee65001425be0b1998",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "converts to",
        },
    },
    {
        "ref": "Evidence:evidence-6059d2519be12b3b9c87",
        "labels": ["Evidence"],
        "props": {
            "post_id": 10,
            "updated_at": "2026-05-12T13:20:56.494000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-6059d2519be12b3b9c87",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "excerpt": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected National Day is almost here, so I wanted to make something festive without buying a "
            "bunch of one-time decorations. I ended up turning a clear plastic bottle into a mini lantern "
            "with a soft red glow inside, and honest",
            "chunk_id": "post-10-v2-c0",
            "url": "/forum/posts/10",
            "raw_predicate": "requires illumination from",
        },
    },
    {
        "ref": "Evidence:evidence-647cb29b85d7c3d64837",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "canonical_relation": "identifies",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-647cb29b85d7c3d64837",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "identifies",
        },
    },
    {
        "ref": "Evidence:evidence-686dd283887852553607",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "canonical_relation": "decorated_with",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-686dd283887852553607",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "decorated with",
        },
    },
    {
        "ref": "Evidence:evidence-709bdede5bbf99ea8cb7",
        "labels": ["Evidence"],
        "props": {
            "post_id": 11,
            "updated_at": "2026-05-12T13:16:23.883000000+00:00",
            "canonical_relation": "reduces_visual_clutter_in",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-709bdede5bbf99ea8cb7",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "excerpt": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋 I finally "
            "replaced the constant stream of disposable batteries in a few small household devices with "
            "rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mo",
            "chunk_id": "post-11-v2-c0",
            "url": "/forum/posts/11",
            "raw_predicate": "reduce",
        },
    },
    {
        "ref": "Evidence:evidence-74b4625bbae9b5a3e619",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "canonical_relation": "may_only_need",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-74b4625bbae9b5a3e619",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "may only need",
        },
    },
    {
        "ref": "Evidence:evidence-77551a38ea39e1f73dd9",
        "labels": ["Evidence"],
        "props": {
            "post_id": 9,
            "updated_at": "2026-05-12T13:15:53.504000000+00:00",
            "canonical_relation": "reduces_visual_clutter_in",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-77551a38ea39e1f73dd9",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "excerpt": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer I needed quick "
            "drawer dividers and really did not want to buy a whole organizer set for one messy kitchen "
            "drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and "
            "used them to separate clips, tea sachets, a",
            "chunk_id": "post-9-v2-c0",
            "url": "/forum/posts/9",
            "raw_predicate": "reduces visual clutter in",
        },
    },
    {
        "ref": "Evidence:evidence-77c3544d8f41bf67e128",
        "labels": ["Evidence"],
        "props": {
            "post_id": 10,
            "updated_at": "2026-05-12T13:20:56.470000000+00:00",
            "canonical_relation": "forms_primary_material_for",
            "extraction_confidence": 0.95,
            "active": True,
            "id": "evidence-77c3544d8f41bf67e128",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "excerpt": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected National Day is almost here, so I wanted to make something festive without buying a "
            "bunch of one-time decorations. I ended up turning a clear plastic bottle into a mini lantern "
            "with a soft red glow inside, and honest",
            "chunk_id": "post-10-v2-c0",
            "url": "/forum/posts/10",
            "raw_predicate": "forms primary material for",
        },
    },
    {
        "ref": "Evidence:evidence-7e1c17ff3b0a66302433",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "canonical_relation": "should_be_documented_via",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-7e1c17ff3b0a66302433",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "should be documented via",
        },
    },
    {
        "ref": "Evidence:evidence-824a03a7de6795b01432",
        "labels": ["Evidence"],
        "props": {
            "post_id": 5,
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "canonical_relation": "accumulates",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-824a03a7de6795b01432",
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "excerpt": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together? I "
            "walked by the riverside path again this morning and noticed the same pattern as last week: "
            "plastic bottles near the benches, snack wrappers caught in the grass, and a surprising number "
            "of cans around the bike parking area. So",
            "chunk_id": "post-5-v2-c0",
            "url": "/forum/posts/5",
            "raw_predicate": "accumulates_debris",
        },
    },
    {
        "ref": "Evidence:evidence-893b723b585cc0aadc26",
        "labels": ["Evidence"],
        "props": {
            "post_id": 12,
            "updated_at": "2026-05-12T13:17:31.713000000+00:00",
            "canonical_relation": "provide_instructions_for",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-893b723b585cc0aadc26",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "excerpt": "The home sorting labels that finally made my family recycle properly ♻️🏷️ I used to explain "
            "the same thing every week: which bin was for paper, which one was for plastic, and why rinsing "
            "containers mattered. Nobody meant to do it wrong, but our setup was too vague. This week I "
            "made simple printed labels for each bin, a",
            "chunk_id": "post-12-v2-c0",
            "url": "/forum/posts/12",
            "raw_predicate": "provide instructions for",
        },
    },
    {
        "ref": "Evidence:evidence-8cb9cd95176667765194",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:19.619000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-8cb9cd95176667765194",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "can be converted into",
        },
    },
    {
        "ref": "Evidence:evidence-8eb122ed9756ad46fa63",
        "labels": ["Evidence"],
        "props": {
            "post_id": 7,
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "canonical_relation": "improve",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-8eb122ed9756ad46fa63",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "excerpt": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨ "
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, "
            "and used them to reorganize my spice sh",
            "chunk_id": "post-7-v2-c0",
            "url": "/forum/posts/7",
            "raw_predicate": "improves_ambiance_of",
        },
    },
    {
        "ref": "Evidence:evidence-94b85e77381d5719bb06",
        "labels": ["Evidence"],
        "props": {
            "post_id": 4,
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "canonical_relation": "organizes_on",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-94b85e77381d5719bb06",
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "excerpt": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades I "
            "cleaned out an empty metal coffee tin this week and turned it into a countertop utensil "
            "holder. It was one of those projects that took almost no time but made the kitchen feel much "
            "more settled. What I did: - washed and dried the t",
            "chunk_id": "post-4-v3-c0",
            "url": "/forum/posts/4",
            "raw_predicate": "organizes on",
        },
    },
    {
        "ref": "Evidence:evidence-95c87502bff0e4a86ab3",
        "labels": ["Evidence"],
        "props": {
            "post_id": 8,
            "updated_at": "2026-05-12T13:16:57.113000000+00:00",
            "canonical_relation": "selects",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-95c87502bff0e4a86ab3",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "excerpt": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss I have "
            "been trying to make my room feel functional without turning every new season into a shopping "
            "event. This time I reused containers, borrowed a desk lamp, and only bought a few essentials "
            "that I knew I would actually use long t",
            "chunk_id": "post-8-v2-c0",
            "url": "/forum/posts/8",
            "raw_predicate": "selects",
        },
    },
    {
        "ref": "Evidence:evidence-98535c71241e6abf3b59",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "canonical_relation": "is_expedited_by",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-98535c71241e6abf3b59",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "is expedited by",
        },
    },
    {
        "ref": "Evidence:evidence-9ad7559148c8dedd6630",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "canonical_relation": "secured_with",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-9ad7559148c8dedd6630",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "secured with",
        },
    },
    {
        "ref": "Evidence:evidence-9d06ba81655e5306b196",
        "labels": ["Evidence"],
        "props": {
            "post_id": 10,
            "updated_at": "2026-05-12T13:20:56.483000000+00:00",
            "canonical_relation": "is_recommended_for_storing",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-9d06ba81655e5306b196",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "excerpt": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected National Day is almost here, so I wanted to make something festive without buying a "
            "bunch of one-time decorations. I ended up turning a clear plastic bottle into a mini lantern "
            "with a soft red glow inside, and honest",
            "chunk_id": "post-10-v2-c0",
            "url": "/forum/posts/10",
            "raw_predicate": "recommended for",
        },
    },
    {
        "ref": "Evidence:evidence-a4ba8d0794980cea9a15",
        "labels": ["Evidence"],
        "props": {
            "post_id": 5,
            "updated_at": "2026-05-12T13:19:49.864000000+00:00",
            "canonical_relation": "aims_to_separate",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-a4ba8d0794980cea9a15",
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "excerpt": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together? I "
            "walked by the riverside path again this morning and noticed the same pattern as last week: "
            "plastic bottles near the benches, snack wrappers caught in the grass, and a surprising number "
            "of cans around the bike parking area. So",
            "chunk_id": "post-5-v2-c0",
            "url": "/forum/posts/5",
            "raw_predicate": "aims_to_separate",
        },
    },
    {
        "ref": "Evidence:evidence-ac979bb6be6ebe73c866",
        "labels": ["Evidence"],
        "props": {
            "post_id": 10,
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "canonical_relation": "encourages_reuse_for",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-ac979bb6be6ebe73c866",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "excerpt": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected National Day is almost here, so I wanted to make something festive without buying a "
            "bunch of one-time decorations. I ended up turning a clear plastic bottle into a mini lantern "
            "with a soft red glow inside, and honest",
            "chunk_id": "post-10-v2-c0",
            "url": "/forum/posts/10",
            "raw_predicate": "encourages reuse for",
        },
    },
    {
        "ref": "Evidence:evidence-b245f8ccf212e780dd1a",
        "labels": ["Evidence"],
        "props": {
            "post_id": 11,
            "updated_at": "2026-05-12T13:16:23.991000000+00:00",
            "canonical_relation": "compatible_with",
            "extraction_confidence": 0.8,
            "active": True,
            "id": "evidence-b245f8ccf212e780dd1a",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "excerpt": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋 I finally "
            "replaced the constant stream of disposable batteries in a few small household devices with "
            "rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mo",
            "chunk_id": "post-11-v2-c0",
            "url": "/forum/posts/11",
            "raw_predicate": "compatible_with",
        },
    },
    {
        "ref": "Evidence:evidence-b5af06345f7b7d41d357",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:19.643000000+00:00",
            "canonical_relation": "is_recommended_for_storing",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-b5af06345f7b7d41d357",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "is recommended for storing",
        },
    },
    {
        "ref": "Evidence:evidence-b5fa747a066f3cb35354",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.133000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-b5fa747a066f3cb35354",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "require terminal protection",
        },
    },
    {
        "ref": "Evidence:evidence-b6576d499c1d89b90d31",
        "labels": ["Evidence"],
        "props": {
            "post_id": 4,
            "updated_at": "2026-05-12T13:15:18.207000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-b6576d499c1d89b90d31",
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "excerpt": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades I "
            "cleaned out an empty metal coffee tin this week and turned it into a countertop utensil "
            "holder. It was one of those projects that took almost no time but made the kitchen feel much "
            "more settled. What I did: - washed and dried the t",
            "chunk_id": "post-4-v3-c0",
            "url": "/forum/posts/4",
            "raw_predicate": "replaces purchase of",
        },
    },
    {
        "ref": "Evidence:evidence-b8b8a1e3609c20411bb0",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:19.747000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-b8b8a1e3609c20411bb0",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "requires",
        },
    },
    {
        "ref": "Evidence:evidence-bee9fe241199a4299770",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "canonical_relation": "reduces_waste_during",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-bee9fe241199a4299770",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "reduces waste during",
        },
    },
    {
        "ref": "Evidence:evidence-c2a893674e4ac459ffec",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.632000000+00:00",
            "canonical_relation": "replaces_purchase_of",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-c2a893674e4ac459ffec",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "replaces",
        },
    },
    {
        "ref": "Evidence:evidence-c2f704b0212adece4f59",
        "labels": ["Evidence"],
        "props": {
            "post_id": 4,
            "updated_at": "2026-05-12T13:15:17.906000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "extraction_confidence": 0.95,
            "active": True,
            "id": "evidence-c2f704b0212adece4f59",
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "excerpt": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades I "
            "cleaned out an empty metal coffee tin this week and turned it into a countertop utensil "
            "holder. It was one of those projects that took almost no time but made the kitchen feel much "
            "more settled. What I did: - washed and dried the t",
            "chunk_id": "post-4-v3-c0",
            "url": "/forum/posts/4",
            "raw_predicate": "repurposed as",
        },
    },
    {
        "ref": "Evidence:evidence-c2fc3650c84e3cae6841",
        "labels": ["Evidence"],
        "props": {
            "post_id": 2,
            "updated_at": "2026-05-12T13:20:26.235000000+00:00",
            "canonical_relation": "require",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-c2fc3650c84e3cae6841",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "excerpt": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier I "
            'used to throw loose batteries into one random drawer and tell myself I would "sort them '
            'later." Later never came, and the drawer became a tiny chaos zone. This month I finally '
            "changed the system, and it made battery recycling f",
            "chunk_id": "post-2-v2-c0",
            "url": "/forum/posts/2",
            "raw_predicate": "require terminal protection",
        },
    },
    {
        "ref": "Evidence:evidence-c9e7256925da0bdb84e4",
        "labels": ["Evidence"],
        "props": {
            "post_id": 9,
            "updated_at": "2026-05-12T13:15:53.431000000+00:00",
            "canonical_relation": "can_be_reused_as",
            "extraction_confidence": 0.95,
            "active": True,
            "id": "evidence-c9e7256925da0bdb84e4",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "excerpt": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer I needed quick "
            "drawer dividers and really did not want to buy a whole organizer set for one messy kitchen "
            "drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and "
            "used them to separate clips, tea sachets, a",
            "chunk_id": "post-9-v2-c0",
            "url": "/forum/posts/9",
            "raw_predicate": "repurposed as",
        },
    },
    {
        "ref": "Evidence:evidence-ccc97b270e6a5c8742b4",
        "labels": ["Evidence"],
        "props": {
            "post_id": 12,
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "canonical_relation": "prioritize",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-ccc97b270e6a5c8742b4",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "excerpt": "The home sorting labels that finally made my family recycle properly ♻️🏷️ I used to explain "
            "the same thing every week: which bin was for paper, which one was for plastic, and why rinsing "
            "containers mattered. Nobody meant to do it wrong, but our setup was too vague. This week I "
            "made simple printed labels for each bin, a",
            "chunk_id": "post-12-v2-c0",
            "url": "/forum/posts/12",
            "raw_predicate": "prioritize",
        },
    },
    {
        "ref": "Evidence:evidence-d6a23f91cc54a1fb93a9",
        "labels": ["Evidence"],
        "props": {
            "post_id": 5,
            "updated_at": "2026-05-12T13:19:49.792000000+00:00",
            "canonical_relation": "scheduled_for",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-d6a23f91cc54a1fb93a9",
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "excerpt": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together? I "
            "walked by the riverside path again this morning and noticed the same pattern as last week: "
            "plastic bottles near the benches, snack wrappers caught in the grass, and a surprising number "
            "of cans around the bike parking area. So",
            "chunk_id": "post-5-v2-c0",
            "url": "/forum/posts/5",
            "raw_predicate": "scheduled_for",
        },
    },
    {
        "ref": "Evidence:evidence-d981d7ad623192580a4b",
        "labels": ["Evidence"],
        "props": {
            "post_id": 9,
            "updated_at": "2026-05-12T13:15:53.574000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-d981d7ad623192580a4b",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "excerpt": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer I needed quick "
            "drawer dividers and really did not want to buy a whole organizer set for one messy kitchen "
            "drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and "
            "used them to separate clips, tea sachets, a",
            "chunk_id": "post-9-v2-c0",
            "url": "/forum/posts/9",
            "raw_predicate": "provides accessible solution for",
        },
    },
    {
        "ref": "Evidence:evidence-dcc643d5f163a57b276e",
        "labels": ["Evidence"],
        "props": {
            "post_id": 10,
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "canonical_relation": "exhibits_aesthetic",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-dcc643d5f163a57b276e",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "excerpt": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected National Day is almost here, so I wanted to make something festive without buying a "
            "bunch of one-time decorations. I ended up turning a clear plastic bottle into a mini lantern "
            "with a soft red glow inside, and honest",
            "chunk_id": "post-10-v2-c0",
            "url": "/forum/posts/10",
            "raw_predicate": "exhibits aesthetic",
        },
    },
    {
        "ref": "Evidence:evidence-e7bf35187ecfa3ca0e53",
        "labels": ["Evidence"],
        "props": {
            "post_id": 3,
            "updated_at": "2026-05-12T13:18:54.581000000+00:00",
            "canonical_relation": "wrapped_with",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-e7bf35187ecfa3ca0e53",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "excerpt": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night I had a "
            "sturdy cardboard mailer left from an online order and almost flattened it for recycling right "
            "away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead ",
            "chunk_id": "post-3-v2-c0",
            "url": "/forum/posts/3",
            "raw_predicate": "wrapped with",
        },
    },
    {
        "ref": "Evidence:evidence-ec1f2e3e220ff01b2890",
        "labels": ["Evidence"],
        "props": {
            "post_id": 1,
            "updated_at": "2026-05-12T13:18:19.833000000+00:00",
            "canonical_relation": "provides_accessible_solution_for",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-ec1f2e3e220ff01b2890",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "excerpt": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful I had one clean "
            "aluminum can sitting on the table after lunch and randomly decided to test whether it could "
            "become a pen holder. After sanding the edge, wrapping the outside with leftover paper, and "
            "adding a simple label, it turned into a desk ",
            "chunk_id": "post-1-v3-c0",
            "url": "/forum/posts/1",
            "raw_predicate": "provides",
        },
    },
    {
        "ref": "Evidence:evidence-ef40ce24f0d8b91cc286",
        "labels": ["Evidence"],
        "props": {
            "post_id": 12,
            "updated_at": "2026-05-12T13:17:31.643000000+00:00",
            "canonical_relation": "reduce_friction_in",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-ef40ce24f0d8b91cc286",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "excerpt": "The home sorting labels that finally made my family recycle properly ♻️🏷️ I used to explain "
            "the same thing every week: which bin was for paper, which one was for plastic, and why rinsing "
            "containers mattered. Nobody meant to do it wrong, but our setup was too vague. This week I "
            "made simple printed labels for each bin, a",
            "chunk_id": "post-12-v2-c0",
            "url": "/forum/posts/12",
            "raw_predicate": "reduce friction in",
        },
    },
    {
        "ref": "Evidence:evidence-f15b5140fbacb473a82c",
        "labels": ["Evidence"],
        "props": {
            "post_id": 6,
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "canonical_relation": "has",
            "extraction_confidence": 0.9,
            "active": True,
            "id": "evidence-f15b5140fbacb473a82c",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "excerpt": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me I "
            "spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back i",
            "chunk_id": "post-6-v2-c0",
            "url": "/forum/posts/6",
            "raw_predicate": "contains",
        },
    },
    {
        "ref": "Evidence:evidence-fd4520c535be33a82e0b",
        "labels": ["Evidence"],
        "props": {
            "post_id": 9,
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "canonical_relation": "is_unnecessary_replacement_for",
            "extraction_confidence": 0.85,
            "active": True,
            "id": "evidence-fd4520c535be33a82e0b",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "excerpt": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer I needed quick "
            "drawer dividers and really did not want to buy a whole organizer set for one messy kitchen "
            "drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, and "
            "used them to separate clips, tea sachets, a",
            "chunk_id": "post-9-v2-c0",
            "url": "/forum/posts/9",
            "raw_predicate": "is unnecessary replacement for",
        },
    },
    {
        "ref": "ForumPost:1",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 1,
            "created_at": "2026-03-29T02:34:00",
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "author_id": 4,
            "url": "/forum/posts/1",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:2",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 2,
            "created_at": "2026-03-29T02:12:00",
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "author_id": 3,
            "url": "/forum/posts/2",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:3",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 3,
            "created_at": "2026-03-29T02:29:00",
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "author_id": 4,
            "url": "/forum/posts/3",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:4",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 4,
            "created_at": "2026-03-29T03:16:00",
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "author_id": 4,
            "url": "/forum/posts/4",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:5",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 5,
            "created_at": "2026-03-29T02:18:00",
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "author_id": 6,
            "url": "/forum/posts/5",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:6",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 6,
            "created_at": "2026-03-29T02:40:00",
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "author_id": 7,
            "url": "/forum/posts/6",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:7",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 7,
            "created_at": "2026-03-29T02:24:00",
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "author_id": 5,
            "url": "/forum/posts/7",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:8",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 8,
            "created_at": "2026-03-29T02:52:00",
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "author_id": 5,
            "url": "/forum/posts/8",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:9",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 9,
            "created_at": "2026-03-29T03:10:00",
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "author_id": 5,
            "url": "/forum/posts/9",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:10",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 10,
            "created_at": "2026-03-29T02:05:00",
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "author_id": 4,
            "url": "/forum/posts/10",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:11",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 11,
            "created_at": "2026-03-29T03:04:00",
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "author_id": 7,
            "url": "/forum/posts/11",
            "status": "published",
        },
    },
    {
        "ref": "ForumPost:12",
        "labels": ["ForumPost"],
        "props": {
            "post_id": 12,
            "created_at": "2026-03-29T02:46:00",
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "author_id": 5,
            "url": "/forum/posts/12",
            "status": "published",
        },
    },
    {
        "ref": "KnowledgeChunk:post-1-v3-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 1,
            "source_type": "forum_post",
            "id": "post-1-v3-c0",
            "source": "/forum/posts/1",
            "text": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful\n"
            "\n"
            "I had one clean aluminum can sitting on the table after lunch and randomly decided to test "
            "whether it could become a pen holder. After sanding the edge, wrapping the outside with leftover "
            "paper, and adding a simple label, it turned into a desk cup that looks much better than I "
            "expected. A few things mattered a lot: - wash it immediately so there is no sticky residue - "
            "smooth the cut edge properly so it feels safe to use - wrap the outside fully so it looks "
            "intentional This kind of project is nice because it takes almost no materials, but still gives "
            'you that small "I made this myself" satisfaction. It is especially good if your desk tends to '
            "collect loose pens, scissors, or charging cables. If you try this, I recommend making two at once "
            "so the setup looks more balanced on a shelf or desk. One can works, but a matching pair feels "
            "much more put together. ✨",
            "source_id": 1,
            "title": "Tiny desk upgrade from a soda can 🥤✂️ surprisingly cute and actually useful",
            "chunk_version": 3,
            "source_url": "/forum/posts/1",
        },
    },
    {
        "ref": "KnowledgeChunk:post-10-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 10,
            "source_type": "forum_post",
            "id": "post-10-v2-c0",
            "text": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected\n"
            "\n"
            "National Day is almost here, so I wanted to make something festive without buying a bunch of "
            "one-time decorations. I ended up turning a clear plastic bottle into a mini lantern with a soft "
            "red glow inside, and honestly it looked so sweet on my windowsill at night. What I used: - 1 "
            "empty transparent plastic bottle - red paper and gold star stickers - a small battery LED light - "
            "scissors, glue, and a little ribbon How I made it: 1. I cleaned the bottle, removed the label, "
            "and cut off the lower section so the shape looked lighter. 2. Then I cut several slim vertical "
            "strips around the body, but kept both ends attached so it could still hold its shape. 3. I "
            "wrapped the top with red ribbon and added a few small gold stars for a festive National Day "
            "feeling. 4. Finally, I placed a small LED light inside and turned it on after dark. What I liked "
            "most was that it still looked handmade, not overly polished. It gave that warm holiday corner "
            "vibe without spending much at all. If you are decorating for National Day and want something "
            "quick, affordable, and easy to photograph, this one is really worth trying. If I remake it, I "
            "would probably hang two or three together at different heights because the glow is even prettier "
            "in a group. Save this idea if you also have too many clean plastic bottles at home and want a "
            "festive excuse to reuse them. 📸",
            "source": "/forum/posts/10",
            "source_id": 10,
            "title": "National Day DIY Lantern from a Plastic Bottle 🇨🇳✨ A tiny project that looked way cuter than I "
            "expected",
            "chunk_version": 2,
            "source_url": "/forum/posts/10",
        },
    },
    {
        "ref": "KnowledgeChunk:post-11-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 11,
            "source_type": "forum_post",
            "id": "post-11-v2-c0",
            "text": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋\n"
            "\n"
            "I finally replaced the constant stream of disposable batteries in a few small household devices "
            "with rechargeable ones, and the change felt surprisingly simple. I started with the remote "
            "controls, a small flashlight, and the wireless mouse I use most often. What made it work: - "
            "choosing just a few high-use devices first - keeping the charger in one obvious place - labeling "
            "the rechargeable set so I would not mix them up with old batteries This did not magically "
            "transform my whole routine overnight, but it immediately reduced the number of loose batteries "
            "collecting in drawers. It also made me more aware of which devices actually burn through power "
            "and might deserve a smarter long-term setup. If you are curious about reducing battery waste "
            "without overcomplicating things, starting small is the move. Pick two or three frequently used "
            "items and build the habit from there. ⚡",
            "source": "/forum/posts/11",
            "source_id": 11,
            "title": "Switching one part of my home to rechargeable batteries was easier than I thought 🔋",
            "chunk_version": 2,
            "source_url": "/forum/posts/11",
        },
    },
    {
        "ref": "KnowledgeChunk:post-12-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 12,
            "source_type": "forum_post",
            "id": "post-12-v2-c0",
            "text": "The home sorting labels that finally made my family recycle properly ♻️🏷️\n"
            "\n"
            "I used to explain the same thing every week: which bin was for paper, which one was for plastic, "
            "and why rinsing containers mattered. Nobody meant to do it wrong, but our setup was too vague. "
            "This week I made simple printed labels for each bin, and the difference was immediate. What I "
            "changed: - clear labels with both words and colors - one tiny note on each bin showing common "
            "examples - a rinse reminder above the plastic bin This is not glamorous content, but it solved a "
            "very real problem in our kitchen. People are much more likely to do the right thing when the "
            'system feels obvious. It also reduced that annoying last-minute "where does this go" conversation '
            "when someone is cleaning up after dinner. If your household recycling still feels messy, I would "
            "honestly start with labels before buying any new containers. A clearer system usually matters "
            "more than prettier bins. 🏠",
            "source": "/forum/posts/12",
            "source_id": 12,
            "title": "The home sorting labels that finally made my family recycle properly ♻️🏷️",
            "chunk_version": 2,
            "source_url": "/forum/posts/12",
        },
    },
    {
        "ref": "KnowledgeChunk:post-2-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 2,
            "source_type": "forum_post",
            "id": "post-2-v2-c0",
            "source": "/forum/posts/2",
            "text": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier\n"
            "\n"
            'I used to throw loose batteries into one random drawer and tell myself I would "sort them later." '
            "Later never came, and the drawer became a tiny chaos zone. This month I finally changed the "
            "system, and it made battery recycling feel so much less annoying. What I do now: - one small box "
            "for AA and AAA batteries - one separate pouch for button batteries - a roll of tape right next to "
            "the box for lithium battery terminals - one note in my phone with nearby drop-off spots My "
            "routine is super simple: 1. Empty the drawer completely. 2. Check which batteries are actually "
            "dead and which still belong to something. 3. Tape the terminals on anything rechargeable or "
            "lithium-based. 4. Group the rest by size so the final drop-off is faster. This sounds tiny, but "
            "the visual difference is huge. I feel much more likely to recycle them properly when everything "
            'is already sorted and safe. If your "battery drawer" has turned into a mystery corner too, try '
            "doing a quick reset before it gets worse. It is one of those boring little tasks that feels "
            "surprisingly satisfying afterward. 🧺",
            "source_id": 2,
            "title": "My Sunday battery drawer reset 🔋 The 10-minute habit that made drop-off day so much easier",
            "chunk_version": 2,
            "source_url": "/forum/posts/2",
        },
    },
    {
        "ref": "KnowledgeChunk:post-3-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 3,
            "source_type": "forum_post",
            "id": "post-3-v2-c0",
            "source": "/forum/posts/3",
            "text": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night\n"
            "\n"
            "I had a sturdy cardboard mailer left from an online order and almost flattened it for recycling "
            "right away, but the shape was too good to waste. So I wrapped it with kraft paper, added a simple "
            "ribbon, and used it as a gift box instead of buying new packaging. What I used: - one clean "
            "cardboard mailer - kraft paper - double-sided tape - ribbon and one small dried flower tag The "
            'nicest part is that the box still looked minimal and neat, not obviously "reused." It actually '
            "felt more thoughtful because I put the packaging together myself. If you give small gifts often, "
            "keeping a few clean mailers aside is genuinely useful. This is one of those low-effort upcycling "
            "ideas that does not need perfection. Even if your folds are slightly uneven, the finished result "
            "still feels warm and personal. Save this if you like wrapping gifts but hate the idea of buying a "
            "new box every single time. 🎁",
            "source_id": 3,
            "title": "Mailing box makeover 📦🎀 I turned a plain cardboard box into a gift box in one night",
            "chunk_version": 2,
            "source_url": "/forum/posts/3",
        },
    },
    {
        "ref": "KnowledgeChunk:post-4-v3-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 4,
            "source_type": "forum_post",
            "id": "post-4-v3-c0",
            "source": "/forum/posts/4",
            "text": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades\n"
            "\n"
            "I cleaned out an empty metal coffee tin this week and turned it into a countertop utensil holder. "
            "It was one of those projects that took almost no time but made the kitchen feel much more "
            "settled. What I did: - washed and dried the tin completely - added a wrap of linen-texture "
            "adhesive paper - labeled the bottom so I would remember when I made it Now my most-used spatulas "
            "and wooden spoons are easy to grab, and I did not have to buy another kitchen container just "
            "because I wanted the counter to look nicer. This kind of upcycling project is small, but that is "
            "exactly why I love it. It feels accessible, useful, and realistic for everyday life. If you have "
            "a sturdy tin at home, do not throw it out too quickly. It might be a better storage piece than "
            "you think. ✨",
            "source_id": 4,
            "title": "Coffee tin to utensil holder ☕️🍴 unexpectedly one of my favorite tiny kitchen upgrades",
            "chunk_version": 3,
            "source_url": "/forum/posts/4",
        },
    },
    {
        "ref": "KnowledgeChunk:post-5-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 5,
            "source_type": "forum_post",
            "id": "post-5-v2-c0",
            "source": "/forum/posts/5",
            "text": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?\n"
            "\n"
            "I walked by the riverside path again this morning and noticed the same pattern as last week: "
            "plastic bottles near the benches, snack wrappers caught in the grass, and a surprising number of "
            "cans around the bike parking area. So I thought, why not make this into a small community cleanup "
            "instead of just complaining about it in my head? My plan is intentionally simple: - Saturday, "
            "9:00 AM - one hour only - gloves, spare bags, and sorting labels provided - no big speeches, just "
            "a practical clean-and-go session I am hoping to separate out obvious recyclables instead of "
            "treating everything as mixed trash. Even if only a few people come, I think it will still feel "
            "good to leave the area noticeably cleaner than we found it. If you like community events that are "
            "casual and actually useful, this is very much that kind of morning. If enough people are "
            "interested, I can also bring cold drinks and mark out two tiny zones so it feels organized rather "
            "than chaotic. Leave a comment if you would join something like this. 🌍",
            "source_id": 5,
            "title": "Weekend riverside cleanup plan 🧤🌿 Anyone wants to do a low-pressure one-hour reset together?",
            "chunk_version": 2,
            "source_url": "/forum/posts/5",
        },
    },
    {
        "ref": "KnowledgeChunk:post-6-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 6,
            "source_type": "forum_post",
            "id": "post-6-v2-c0",
            "source": "/forum/posts/6",
            "text": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me\n"
            "\n"
            "I spent this afternoon going through my desk drawer and found three dead charging cables, one "
            "broken mouse, an old power bank that no longer holds charge, and a phone stand I forgot I even "
            "owned. Instead of tossing everything back into the drawer, I made a small e-waste sorting pile "
            "for my next recycling trip. What I separated: - broken cables and adapters - small damaged "
            "peripherals - a dead power bank - things that only needed cleaning or a tiny repair The biggest "
            "lesson: not everything in an e-waste pile is actually waste. One keyboard just needed dust "
            "removal and a new cable, while the power bank definitely belongs in proper recycling. Doing a "
            "quick category check first makes the final drop-off smarter and less wasteful. If you have a tech "
            "drawer that has turned into a graveyard, try a 20-minute reset. Even if you do not fix anything "
            "today, you will at least know what needs repair, what can be donated, and what should be recycled "
            "responsibly. 🔧",
            "source_id": 6,
            "title": "My e-waste desk reset before drop-off day 💻🔌 the cable pile finally stopped haunting me",
            "chunk_version": 2,
            "source_url": "/forum/posts/6",
        },
    },
    {
        "ref": "KnowledgeChunk:post-7-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 7,
            "source_type": "forum_post",
            "id": "post-7-v2-c0",
            "source": "/forum/posts/7",
            "text": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨\n"
            "\n"
            "I had been keeping random jam jars for months because I felt guilty throwing them away, but I "
            "also had no clear plan for them. This week I cleaned six matching jars, added simple labels, and "
            "used them to reorganize my spice shelf. It ended up looking way more cohesive than I expected. "
            "What helped most: - soaking the jars in warm water first so the labels came off cleanly - drying "
            "them overnight to avoid trapped moisture - using one style of label so everything looked "
            'intentional The result is not dramatic in a "before and after" kind of way, but it changed the '
            "feeling of the whole shelf. I can see what I have, I am less likely to rebuy duplicates, and the "
            "jars actually feel like part of the kitchen instead of leftover packaging. If you have a few "
            "sturdy glass jars at home, this is one of the easiest upgrades to try. Low effort, almost free, "
            "and very satisfying if you enjoy little home resets. 🤍",
            "source_id": 7,
            "title": "I finally reused old glass jars for my spice shelf and my kitchen looks so much calmer now 🫙✨",
            "chunk_version": 2,
            "source_url": "/forum/posts/7",
        },
    },
    {
        "ref": "KnowledgeChunk:post-8-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 8,
            "source_type": "forum_post",
            "id": "post-8-v2-c0",
            "source": "/forum/posts/8",
            "text": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss\n"
            "\n"
            "I have been trying to make my room feel functional without turning every new season into a "
            "shopping event. This time I reused containers, borrowed a desk lamp, and only bought a few "
            "essentials that I knew I would actually use long term. What I skipped on purpose: - decorative "
            "storage boxes I did not truly need - trendy acrylic organizers that looked nice but solved no "
            "real problem - duplicate mugs and kitchen accessories What worked better instead: - reusing jars "
            "and trays I already had - choosing one solid laundry basket and one sturdy tote - keeping "
            "surfaces clear so the room felt calmer by default This approach is less exciting in the "
            "beginning, but I always feel better a month later because the room stays easier to manage. If you "
            "are setting up a dorm or small apartment soon, a low-buy start is genuinely underrated. You "
            "notice very quickly which things you actually need and which ones were just impulse purchases "
            "with good lighting in the ad. ☁️",
            "source_id": 8,
            "title": "My low-buy dorm room starter list 🌿 things I skipped, reused, and honestly did not miss",
            "chunk_version": 2,
            "source_url": "/forum/posts/8",
        },
    },
    {
        "ref": "KnowledgeChunk:post-9-v2-c0",
        "labels": ["KnowledgeChunk"],
        "props": {
            "chunk_index": 0,
            "post_id": 9,
            "source_type": "forum_post",
            "id": "post-9-v2-c0",
            "source": "/forum/posts/9",
            "text": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer\n"
            "\n"
            "I needed quick drawer dividers and really did not want to buy a whole organizer set for one messy "
            "kitchen drawer. So I cut down a few sturdy paper shopping bags, folded them into simple sleeves, "
            "and used them to separate clips, tea sachets, and random little packets. What surprised me most "
            "was how neat it looked once everything had a place. The brown paper also made the drawer feel "
            "visually calmer compared to a mix of loose plastic packaging. Would this survive forever? "
            "Probably not. But for a no-spend fix using something I already had at home, it worked incredibly "
            "well. If you are in a home-reset mood and want something low effort but actually useful, try this "
            "before buying a new organizer. 📦",
            "source_id": 9,
            "title": "Paper bag drawer dividers 🧺 a zero-cost trick for the messiest kitchen drawer",
            "chunk_version": 2,
            "source_url": "/forum/posts/9",
        },
    },
    {
        "ref": "RelationFact:fact-0042790fc1e238c472af",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.619000000+00:00",
            "object_key": "pen_holder",
            "confidence": 0.9,
            "relation_key": "can_be_reused_as",
            "id": "fact-0042790fc1e238c472af",
            "support_count": 1,
            "subject_key": "aluminum_can",
        },
    },
    {
        "ref": "RelationFact:fact-0547469d9c71745dcc57",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.274000000+00:00",
            "object_key": "dorm_room",
            "confidence": 0.9,
            "relation_key": "enhances",
            "id": "fact-0547469d9c71745dcc57",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-05e5356d27d8ed09be12",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.542000000+00:00",
            "object_key": "responsible_recycling",
            "confidence": 0.95,
            "relation_key": "require",
            "id": "fact-05e5356d27d8ed09be12",
            "support_count": 1,
            "subject_key": "power_bank",
        },
    },
    {
        "ref": "RelationFact:fact-094ce29c13c649beb84e",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.286000000+00:00",
            "object_key": "spice_shelf",
            "confidence": 0.9,
            "relation_key": "repurposed_for",
            "id": "fact-094ce29c13c649beb84e",
            "support_count": 1,
            "subject_key": "glass_jars",
        },
    },
    {
        "ref": "RelationFact:fact-13ff9e845580d253cfec",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.643000000+00:00",
            "object_key": "kitchen",
            "confidence": 0.85,
            "relation_key": "reduce_friction_in",
            "id": "fact-13ff9e845580d253cfec",
            "support_count": 1,
            "subject_key": "household_recycling",
        },
    },
    {
        "ref": "RelationFact:fact-194edfd0054ea27e3d98",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "object_key": "ribbon",
            "confidence": 0.9,
            "relation_key": "decorated_with",
            "id": "fact-194edfd0054ea27e3d98",
            "support_count": 1,
            "subject_key": "gift_box",
        },
    },
    {
        "ref": "RelationFact:fact-19f82c23ed2794c48e62",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "object_key": "double_sided_tape",
            "confidence": 0.85,
            "relation_key": "secured_with",
            "id": "fact-19f82c23ed2794c48e62",
            "support_count": 1,
            "subject_key": "kraft_paper",
        },
    },
    {
        "ref": "RelationFact:fact-2223962ae695cf302f32",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "object_key": "recycling_bins",
            "confidence": 0.9,
            "relation_key": "prioritize",
            "id": "fact-2223962ae695cf302f32",
            "support_count": 1,
            "subject_key": "household_recycling",
        },
    },
    {
        "ref": "RelationFact:fact-22f8a37933bc642bf853",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.423000000+00:00",
            "object_key": "e_waste",
            "confidence": 0.9,
            "relation_key": "accumulates",
            "id": "fact-22f8a37933bc642bf853",
            "support_count": 1,
            "subject_key": "desk_drawer",
        },
    },
    {
        "ref": "RelationFact:fact-29558dffbf760b96dad7",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "object_key": "kitchen_countertop",
            "confidence": 0.85,
            "relation_key": "organizes_on",
            "id": "fact-29558dffbf760b96dad7",
            "support_count": 1,
            "subject_key": "utensil_holder",
        },
    },
    {
        "ref": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.256000000+00:00",
            "object_key": "desk_lamp",
            "confidence": 0.9,
            "relation_key": "borrows",
            "id": "fact-2e4a8e8fbe178670a5fc",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-3026d76c11729aa75d75",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.483000000+00:00",
            "object_key": "national_day",
            "confidence": 0.9,
            "relation_key": "is_recommended_for_storing",
            "id": "fact-3026d76c11729aa75d75",
            "support_count": 1,
            "subject_key": "diy_lantern",
        },
    },
    {
        "ref": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.129000000+00:00",
            "object_key": "surfaces",
            "confidence": 0.85,
            "relation_key": "keeps_clear",
            "id": "fact-33c46aec0bd9ccc1bec9",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.494000000+00:00",
            "object_key": "led_light",
            "confidence": 0.9,
            "relation_key": "require",
            "id": "fact-3831b81b601d1e3d4b9b",
            "support_count": 1,
            "subject_key": "diy_lantern",
        },
    },
    {
        "ref": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.235000000+00:00",
            "object_key": "electrical_tape",
            "confidence": 0.85,
            "relation_key": "require",
            "id": "fact-3c1ee445188ba98f6d5e",
            "support_count": 1,
            "subject_key": "rechargeable_batteries",
        },
    },
    {
        "ref": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "object_key": "pre_sorted_organization",
            "confidence": 0.85,
            "relation_key": "is_expedited_by",
            "id": "fact-3cba1d4cb61f3a49a1a3",
            "support_count": 1,
            "subject_key": "battery_recycling",
        },
    },
    {
        "ref": "RelationFact:fact-458add0bdec4a9a8165d",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "object_key": "cleaning_supplies",
            "confidence": 0.9,
            "relation_key": "provides_accessible_solution_for",
            "id": "fact-458add0bdec4a9a8165d",
            "support_count": 1,
            "subject_key": "cleanup_session",
        },
    },
    {
        "ref": "RelationFact:fact-4729b75726640103591d",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.713000000+00:00",
            "object_key": "recycling_bins",
            "confidence": 0.8,
            "relation_key": "provide_instructions_for",
            "id": "fact-4729b75726640103591d",
            "support_count": 1,
            "subject_key": "sorting_labels",
        },
    },
    {
        "ref": "RelationFact:fact-49c91518b55a5cddc2b5",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "object_key": "litter",
            "confidence": 0.9,
            "relation_key": "accumulates",
            "id": "fact-49c91518b55a5cddc2b5",
            "support_count": 1,
            "subject_key": "riverside_path",
        },
    },
    {
        "ref": "RelationFact:fact-4b167573656803ef312c",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.581000000+00:00",
            "object_key": "kraft_paper",
            "confidence": 0.9,
            "relation_key": "wrapped_with",
            "id": "fact-4b167573656803ef312c",
            "support_count": 1,
            "subject_key": "cardboard_mailer",
        },
    },
    {
        "ref": "RelationFact:fact-50d5618b306780063992",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "object_key": "handmade_appearance",
            "relation_key": "exhibits_aesthetic",
            "confidence": 0.85,
            "id": "fact-50d5618b306780063992",
            "support_count": 1,
            "subject_key": "diy_lantern",
        },
    },
    {
        "ref": "RelationFact:fact-546d15efb08e221cf2dd",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "object_key": "aa_batteries",
            "confidence": 0.85,
            "relation_key": "should_segregate",
            "id": "fact-546d15efb08e221cf2dd",
            "support_count": 1,
            "subject_key": "storage_containers",
        },
    },
    {
        "ref": "RelationFact:fact-576a33c4db476e2b60d4",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.864000000+00:00",
            "object_key": "recyclables",
            "confidence": 0.85,
            "relation_key": "aims_to_separate",
            "id": "fact-576a33c4db476e2b60d4",
            "support_count": 1,
            "subject_key": "cleanup_session",
        },
    },
    {
        "ref": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.812000000+00:00",
            "object_key": "disposable_batteries",
            "confidence": 0.9,
            "relation_key": "replaces_purchase_of",
            "id": "fact-5b2b8f860e311e95f5bb",
            "support_count": 1,
            "subject_key": "rechargeable_batteries",
        },
    },
    {
        "ref": "RelationFact:fact-60975c819ea80a37a2e7",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.394000000+00:00",
            "object_key": "duplicate_purchases",
            "relation_key": "minimizes",
            "confidence": 0.85,
            "id": "fact-60975c819ea80a37a2e7",
            "support_count": 1,
            "subject_key": "consistent_labeling",
        },
    },
    {
        "ref": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.628000000+00:00",
            "object_key": "sorting_labels",
            "confidence": 0.9,
            "relation_key": "require",
            "id": "fact-62430e7f1d9b6d31b41f",
            "support_count": 1,
            "subject_key": "recycling_bins",
        },
    },
    {
        "ref": "RelationFact:fact-69248e4b2a5afb0db0df",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "object_key": "remaining_functionality",
            "relation_key": "should_be_evaluated_for",
            "confidence": 0.85,
            "id": "fact-69248e4b2a5afb0db0df",
            "support_count": 1,
            "subject_key": "used_batteries",
        },
    },
    {
        "ref": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.632000000+00:00",
            "object_key": "new_packaging",
            "confidence": 0.85,
            "relation_key": "replaces_purchase_of",
            "id": "fact-6dba8a8c2dfa70cdcffc",
            "support_count": 1,
            "subject_key": "upcycling",
        },
    },
    {
        "ref": "RelationFact:fact-7333437cb5932c1a0d6f",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "object_key": "immediate_washing",
            "confidence": 0.9,
            "relation_key": "is_avoided_by",
            "id": "fact-7333437cb5932c1a0d6f",
            "support_count": 1,
            "subject_key": "sticky_residue",
        },
    },
    {
        "ref": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.991000000+00:00",
            "object_key": "rechargeable_batteries",
            "confidence": 0.8,
            "relation_key": "compatible_with",
            "id": "fact-74ac803fbdf31b9d39ac",
            "support_count": 1,
            "subject_key": "flashlight",
        },
    },
    {
        "ref": "RelationFact:fact-755576d6ba38127cb4a6",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.133000000+00:00",
            "object_key": "electrical_tape",
            "confidence": 0.9,
            "relation_key": "require",
            "id": "fact-755576d6ba38127cb4a6",
            "support_count": 1,
            "subject_key": "lithium_batteries",
        },
    },
    {
        "ref": "RelationFact:fact-7a274e626c596c992df5",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.470000000+00:00",
            "object_key": "diy_lantern",
            "confidence": 0.95,
            "relation_key": "forms_primary_material_for",
            "id": "fact-7a274e626c596c992df5",
            "support_count": 1,
            "subject_key": "plastic_bottle",
        },
    },
    {
        "ref": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "object_key": "digital_notes",
            "confidence": 0.8,
            "relation_key": "should_be_documented_via",
            "id": "fact-7ec76661b8608c0a0fe1",
            "support_count": 1,
            "subject_key": "drop_off_locations",
        },
    },
    {
        "ref": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:24.064000000+00:00",
            "object_key": "rechargeable_batteries",
            "confidence": 0.8,
            "relation_key": "compatible_with",
            "id": "fact-81d7a259bb01fffe7bfe",
            "support_count": 1,
            "subject_key": "wireless_mouse",
        },
    },
    {
        "ref": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.241000000+00:00",
            "object_key": "impulse_purchases",
            "confidence": 0.8,
            "relation_key": "filters",
            "id": "fact-848a6c48d1d01f2e92f2",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-84cae26b50128796d354",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:17:31.612000000+00:00",
            "object_key": "household_recycling",
            "confidence": 0.95,
            "relation_key": "improve",
            "id": "fact-84cae26b50128796d354",
            "support_count": 1,
            "subject_key": "sorting_labels",
        },
    },
    {
        "ref": "RelationFact:fact-8beb84f279311656bef1",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "object_key": "cleaning",
            "confidence": 0.85,
            "relation_key": "may_only_need",
            "id": "fact-8beb84f279311656bef1",
            "support_count": 1,
            "subject_key": "keyboard",
        },
    },
    {
        "ref": "RelationFact:fact-8d603e53dfdca6798ca8",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.988000000+00:00",
            "object_key": "jars",
            "confidence": 0.85,
            "relation_key": "can_be_reused_as",
            "id": "fact-8d603e53dfdca6798ca8",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-8de82e9dc1dd367598d2",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.504000000+00:00",
            "object_key": "kitchen_drawer",
            "confidence": 0.9,
            "relation_key": "reduces_visual_clutter_in",
            "id": "fact-8de82e9dc1dd367598d2",
            "support_count": 1,
            "subject_key": "drawer_divider",
        },
    },
    {
        "ref": "RelationFact:fact-9963222c51712162f9e0",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.431000000+00:00",
            "object_key": "drawer_divider",
            "confidence": 0.95,
            "relation_key": "can_be_reused_as",
            "id": "fact-9963222c51712162f9e0",
            "support_count": 1,
            "subject_key": "paper_bag",
        },
    },
    {
        "ref": "RelationFact:fact-9eab4dea6c51e2066546",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "object_key": "imperfect_execution",
            "confidence": 0.85,
            "relation_key": "tolerates",
            "id": "fact-9eab4dea6c51e2066546",
            "support_count": 1,
            "subject_key": "upcycling",
        },
    },
    {
        "ref": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "object_key": "non_waste_items",
            "confidence": 0.9,
            "relation_key": "has",
            "id": "fact-9ed4387cd0a85b3b6b09",
            "support_count": 1,
            "subject_key": "e_waste",
        },
    },
    {
        "ref": "RelationFact:fact-a7079f73f8eb5c487730",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "object_key": "visual_balance",
            "confidence": 0.8,
            "relation_key": "enhances",
            "id": "fact-a7079f73f8eb5c487730",
            "support_count": 1,
            "subject_key": "matching_pair",
        },
    },
    {
        "ref": "RelationFact:fact-a7aefc0c9c9593776348",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:17.906000000+00:00",
            "object_key": "utensil_holder",
            "confidence": 0.95,
            "relation_key": "can_be_reused_as",
            "id": "fact-a7aefc0c9c9593776348",
            "support_count": 1,
            "subject_key": "coffee_tin",
        },
    },
    {
        "ref": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:57.113000000+00:00",
            "object_key": "tote",
            "confidence": 0.85,
            "relation_key": "selects",
            "id": "fact-a9fbcbbad7d7e2cd2337",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-aa4483d4fc5be4197267",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.833000000+00:00",
            "object_key": "intentional_aesthetic",
            "relation_key": "provides_accessible_solution_for",
            "confidence": 0.85,
            "id": "fact-aa4483d4fc5be4197267",
            "support_count": 1,
            "subject_key": "paper_wrap",
        },
    },
    {
        "ref": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "object_key": "zero_cost_hack",
            "confidence": 0.85,
            "relation_key": "is_unnecessary_replacement_for",
            "id": "fact-b665d8dcdb5c06ca24cd",
            "support_count": 1,
            "subject_key": "commercial_organizer",
        },
    },
    {
        "ref": "RelationFact:fact-bd130e3440285e314333",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "object_key": "disposal_options",
            "confidence": 0.8,
            "relation_key": "identifies",
            "id": "fact-bd130e3440285e314333",
            "support_count": 1,
            "subject_key": "tech_drawer_reset",
        },
    },
    {
        "ref": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.001000000+00:00",
            "object_key": "coffee_tin",
            "confidence": 0.9,
            "relation_key": "applied_to_exterior_of",
            "id": "fact-c09c61b0de8ffa1a575b",
            "support_count": 1,
            "subject_key": "adhesive_paper",
        },
    },
    {
        "ref": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.894000000+00:00",
            "object_key": "rechargeable_batteries",
            "confidence": 0.8,
            "relation_key": "compatible_with",
            "id": "fact-c0b37ff31e6db0ca7b84",
            "support_count": 1,
            "subject_key": "remote_controls",
        },
    },
    {
        "ref": "RelationFact:fact-c30d4f82e7b4912c5446",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "object_key": "drop_off",
            "confidence": 0.9,
            "relation_key": "reduces_waste_during",
            "id": "fact-c30d4f82e7b4912c5446",
            "support_count": 1,
            "subject_key": "category_check",
        },
    },
    {
        "ref": "RelationFact:fact-c903d0168876dbb8ba96",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "object_key": "kitchen",
            "confidence": 0.85,
            "relation_key": "improve",
            "id": "fact-c903d0168876dbb8ba96",
            "support_count": 1,
            "subject_key": "spice_shelf",
        },
    },
    {
        "ref": "RelationFact:fact-cc66c3b40366f651ab0f",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.574000000+00:00",
            "object_key": "kitchen_drawer",
            "confidence": 0.9,
            "relation_key": "provides_accessible_solution_for",
            "id": "fact-cc66c3b40366f651ab0f",
            "support_count": 1,
            "subject_key": "zero_cost_hack",
        },
    },
    {
        "ref": "RelationFact:fact-cca25498c9babd07a929",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:54.483000000+00:00",
            "object_key": "gift_box",
            "confidence": 0.9,
            "relation_key": "can_be_reused_as",
            "id": "fact-cca25498c9babd07a929",
            "support_count": 1,
            "subject_key": "cardboard_mailer",
        },
    },
    {
        "ref": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "object_key": "packaging_waste",
            "confidence": 0.8,
            "relation_key": "eliminates_concern_about",
            "id": "fact-cef84f8f3c4769fe08b4",
            "support_count": 1,
            "subject_key": "glass_jars",
        },
    },
    {
        "ref": "RelationFact:fact-d7e611f93698ff7506ae",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "object_key": "festive_craft_reuse",
            "relation_key": "encourages_reuse_for",
            "confidence": 0.9,
            "id": "fact-d7e611f93698ff7506ae",
            "support_count": 1,
            "subject_key": "plastic_bottle",
        },
    },
    {
        "ref": "RelationFact:fact-daf9403c2d40902e8fbe",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:49.792000000+00:00",
            "object_key": "saturday",
            "confidence": 0.9,
            "relation_key": "scheduled_for",
            "id": "fact-daf9403c2d40902e8fbe",
            "support_count": 1,
            "subject_key": "cleanup_session",
        },
    },
    {
        "ref": "RelationFact:fact-de71ec0b6c56f799e56c",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:18.207000000+00:00",
            "object_key": "kitchen_containers",
            "relation_key": "replaces_purchase_of",
            "confidence": 0.9,
            "id": "fact-de71ec0b6c56f799e56c",
            "support_count": 1,
            "subject_key": "coffee_tin",
        },
    },
    {
        "ref": "RelationFact:fact-defbba56909591fcdaaa",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:15:53.633000000+00:00",
            "object_key": "long_term_storage",
            "confidence": 0.85,
            "relation_key": "has",
            "id": "fact-defbba56909591fcdaaa",
            "support_count": 1,
            "subject_key": "drawer_divider",
        },
    },
    {
        "ref": "RelationFact:fact-e0e8da778fcefd0b8873",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.747000000+00:00",
            "object_key": "sanding",
            "confidence": 0.9,
            "relation_key": "require",
            "id": "fact-e0e8da778fcefd0b8873",
            "support_count": 1,
            "subject_key": "cut_edge",
        },
    },
    {
        "ref": "RelationFact:fact-ef2bed229e62219b456a",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "object_key": "inventory_tracking",
            "relation_key": "enables",
            "confidence": 0.8,
            "id": "fact-ef2bed229e62219b456a",
            "support_count": 1,
            "subject_key": "consistent_labeling",
        },
    },
    {
        "ref": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:18:19.643000000+00:00",
            "object_key": "loose_stationery",
            "confidence": 0.85,
            "relation_key": "is_recommended_for_storing",
            "id": "fact-ef45dc619e1e8ac9048a",
            "support_count": 1,
            "subject_key": "pen_holder",
        },
    },
    {
        "ref": "RelationFact:fact-f2b6ee037bb9837292da",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:23.883000000+00:00",
            "object_key": "battery_waste",
            "confidence": 0.85,
            "relation_key": "reduces_visual_clutter_in",
            "id": "fact-f2b6ee037bb9837292da",
            "support_count": 1,
            "subject_key": "rechargeable_batteries",
        },
    },
    {
        "ref": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.821000000+00:00",
            "object_key": "decorative_storage_boxes",
            "confidence": 0.9,
            "relation_key": "has",
            "id": "fact-fc25f6300d71d4c93fa9",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "labels": ["RelationFact"],
        "props": {
            "updated_at": "2026-05-12T13:16:56.892000000+00:00",
            "object_key": "acrylic_organizers",
            "confidence": 0.85,
            "relation_key": "rejects",
            "id": "fact-fdc0a1d45319d8a4e238",
            "support_count": 1,
            "subject_key": "low_buy_approach",
        },
    },
    {
        "ref": "RelationType:accumulates",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["accumulates"],
            "updated_at": "2026-05-12T13:19:49.880000000+00:00",
            "confidence": 0.9,
            "label": "accumulates",
            "created_by": "existing_similarity",
            "key": "accumulates",
        },
    },
    {
        "ref": "RelationType:aims_to_separate",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["aims_to_separate"],
            "updated_at": "2026-05-12T13:19:49.864000000+00:00",
            "confidence": 0.72,
            "label": "aims_to_separate",
            "created_by": "created_from_predicate",
            "key": "aims_to_separate",
        },
    },
    {
        "ref": "RelationType:applied_to_exterior_of",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["applied to exterior of"],
            "updated_at": "2026-05-12T13:15:18.001000000+00:00",
            "confidence": 0.72,
            "label": "applied to exterior of",
            "created_by": "created_from_predicate",
            "key": "applied_to_exterior_of",
        },
    },
    {
        "ref": "RelationType:borrows",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["borrows"],
            "updated_at": "2026-05-12T13:16:57.256000000+00:00",
            "confidence": 0.72,
            "label": "borrows",
            "created_by": "created_from_predicate",
            "key": "borrows",
        },
    },
    {
        "ref": "RelationType:can_be_reused_as",
        "labels": ["RelationType"],
        "props": {
            "aliases": [
                "can be reused as",
                "convert into",
                "converted into",
                "repurpose as",
                "repurposed as",
                "reuse as",
                "reused as",
                "turn into",
                "turned into",
                "upcycle into",
                "upcycled into",
                "做成",
                "再利用为",
                "变成",
                "改为",
                "改造成",
            ],
            "updated_at": "2026-05-12T13:18:54.483000000+00:00",
            "confidence": 1.0,
            "label": "can be reused as",
            "created_by": "seed",
            "key": "can_be_reused_as",
        },
    },
    {
        "ref": "RelationType:compatible_with",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["compatible_with"],
            "updated_at": "2026-05-12T13:16:24.064000000+00:00",
            "confidence": 1.0,
            "label": "compatible_with",
            "created_by": "existing_similarity",
            "key": "compatible_with",
        },
    },
    {
        "ref": "RelationType:decorated_with",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["decorated with"],
            "updated_at": "2026-05-12T13:18:54.614000000+00:00",
            "confidence": 0.72,
            "label": "decorated with",
            "created_by": "created_from_predicate",
            "key": "decorated_with",
        },
    },
    {
        "ref": "RelationType:eliminates_concern_about",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["eliminates_concern_about"],
            "updated_at": "2026-05-12T13:19:32.409000000+00:00",
            "confidence": 0.72,
            "label": "eliminates_concern_about",
            "created_by": "created_from_predicate",
            "key": "eliminates_concern_about",
        },
    },
    {
        "ref": "RelationType:enables",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["enables"],
            "updated_at": "2026-05-12T13:19:32.422000000+00:00",
            "confidence": 0.72,
            "label": "enables",
            "created_by": "created_from_predicate",
            "key": "enables",
        },
    },
    {
        "ref": "RelationType:encourages_reuse_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["encourages reuse for"],
            "updated_at": "2026-05-12T13:20:56.583000000+00:00",
            "confidence": 0.72,
            "label": "encourages reuse for",
            "created_by": "created_from_predicate",
            "key": "encourages_reuse_for",
        },
    },
    {
        "ref": "RelationType:enhances",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["enhances"],
            "updated_at": "2026-05-12T13:18:20.020000000+00:00",
            "confidence": 1.0,
            "label": "enhances",
            "created_by": "existing_similarity",
            "key": "enhances",
        },
    },
    {
        "ref": "RelationType:exhibits_aesthetic",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["exhibits aesthetic"],
            "updated_at": "2026-05-12T13:20:56.573000000+00:00",
            "confidence": 0.72,
            "label": "exhibits aesthetic",
            "created_by": "created_from_predicate",
            "key": "exhibits_aesthetic",
        },
    },
    {
        "ref": "RelationType:filters",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["filters"],
            "updated_at": "2026-05-12T13:16:57.241000000+00:00",
            "confidence": 0.72,
            "label": "filters",
            "created_by": "created_from_predicate",
            "key": "filters",
        },
    },
    {
        "ref": "RelationType:forms_primary_material_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["forms primary material for"],
            "updated_at": "2026-05-12T13:20:56.470000000+00:00",
            "confidence": 0.72,
            "label": "forms primary material for",
            "created_by": "created_from_predicate",
            "key": "forms_primary_material_for",
        },
    },
    {
        "ref": "RelationType:has",
        "labels": ["RelationType"],
        "props": {
            "aliases": [
                "contain",
                "contains",
                "has",
                "have",
                "hold",
                "holds",
                "own",
                "owns",
                "possess",
                "possesses",
                "包含",
                "含有",
                "拥有",
                "持有",
            ],
            "updated_at": "2026-05-12T13:18:02.439000000+00:00",
            "confidence": 1.0,
            "label": "has",
            "created_by": "seed",
            "key": "has",
        },
    },
    {
        "ref": "RelationType:identifies",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["identifies"],
            "updated_at": "2026-05-12T13:18:02.670000000+00:00",
            "confidence": 0.72,
            "label": "identifies",
            "created_by": "created_from_predicate",
            "key": "identifies",
        },
    },
    {
        "ref": "RelationType:improve",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["improve"],
            "updated_at": "2026-05-12T13:19:32.304000000+00:00",
            "confidence": 0.9,
            "label": "improve",
            "created_by": "existing_similarity",
            "key": "improve",
        },
    },
    {
        "ref": "RelationType:is_avoided_by",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["is avoided by"],
            "updated_at": "2026-05-12T13:18:19.927000000+00:00",
            "confidence": 0.72,
            "label": "is avoided by",
            "created_by": "created_from_predicate",
            "key": "is_avoided_by",
        },
    },
    {
        "ref": "RelationType:is_expedited_by",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["is expedited by"],
            "updated_at": "2026-05-12T13:20:26.264000000+00:00",
            "confidence": 0.72,
            "label": "is expedited by",
            "created_by": "created_from_predicate",
            "key": "is_expedited_by",
        },
    },
    {
        "ref": "RelationType:is_recommended_for_storing",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["is recommended for storing"],
            "updated_at": "2026-05-12T13:20:56.483000000+00:00",
            "confidence": 0.9,
            "label": "is recommended for storing",
            "created_by": "existing_similarity",
            "key": "is_recommended_for_storing",
        },
    },
    {
        "ref": "RelationType:is_unnecessary_replacement_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["is unnecessary replacement for"],
            "updated_at": "2026-05-12T13:15:53.718000000+00:00",
            "confidence": 0.72,
            "label": "is unnecessary replacement for",
            "created_by": "created_from_predicate",
            "key": "is_unnecessary_replacement_for",
        },
    },
    {
        "ref": "RelationType:keeps_clear",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["keeps clear"],
            "updated_at": "2026-05-12T13:16:57.129000000+00:00",
            "confidence": 0.72,
            "label": "keeps clear",
            "created_by": "created_from_predicate",
            "key": "keeps_clear",
        },
    },
    {
        "ref": "RelationType:made_of",
        "labels": ["RelationType"],
        "props": {
            "aliases": [
                "composed of",
                "consists of",
                "made from",
                "made of",
                "material is",
                "材质是",
                "由 制成",
                "由制成",
                "组成",
            ],
            "confidence": 1.0,
            "label": "made of",
            "created_by": "seed",
            "key": "made_of",
        },
    },
    {
        "ref": "RelationType:may_only_need",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["may only need"],
            "updated_at": "2026-05-12T13:18:02.629000000+00:00",
            "confidence": 0.72,
            "label": "may only need",
            "created_by": "created_from_predicate",
            "key": "may_only_need",
        },
    },
    {
        "ref": "RelationType:minimizes",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["minimizes"],
            "updated_at": "2026-05-12T13:19:32.394000000+00:00",
            "confidence": 0.72,
            "label": "minimizes",
            "created_by": "created_from_predicate",
            "key": "minimizes",
        },
    },
    {
        "ref": "RelationType:organizes_on",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["organizes on"],
            "updated_at": "2026-05-12T13:15:18.123000000+00:00",
            "confidence": 0.72,
            "label": "organizes on",
            "created_by": "created_from_predicate",
            "key": "organizes_on",
        },
    },
    {
        "ref": "RelationType:prioritize",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["prioritize"],
            "updated_at": "2026-05-12T13:17:31.782000000+00:00",
            "confidence": 0.72,
            "label": "prioritize",
            "created_by": "created_from_predicate",
            "key": "prioritize",
        },
    },
    {
        "ref": "RelationType:provide_instructions_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["provide instructions for"],
            "updated_at": "2026-05-12T13:17:31.713000000+00:00",
            "confidence": 0.72,
            "label": "provide instructions for",
            "created_by": "created_from_predicate",
            "key": "provide_instructions_for",
        },
    },
    {
        "ref": "RelationType:provides_accessible_solution_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["provides accessible solution for"],
            "updated_at": "2026-05-12T13:19:49.894000000+00:00",
            "confidence": 0.9,
            "label": "provides accessible solution for",
            "created_by": "existing_similarity",
            "key": "provides_accessible_solution_for",
        },
    },
    {
        "ref": "RelationType:reduce_friction_in",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["reduce friction in"],
            "updated_at": "2026-05-12T13:17:31.643000000+00:00",
            "confidence": 0.72,
            "label": "reduce friction in",
            "created_by": "created_from_predicate",
            "key": "reduce_friction_in",
        },
    },
    {
        "ref": "RelationType:reduces_visual_clutter_in",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["reduces visual clutter in"],
            "updated_at": "2026-05-12T13:16:23.883000000+00:00",
            "confidence": 0.9,
            "label": "reduces visual clutter in",
            "created_by": "existing_similarity",
            "key": "reduces_visual_clutter_in",
        },
    },
    {
        "ref": "RelationType:reduces_waste_during",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["reduces waste during"],
            "updated_at": "2026-05-12T13:18:02.649000000+00:00",
            "confidence": 0.72,
            "label": "reduces waste during",
            "created_by": "created_from_predicate",
            "key": "reduces_waste_during",
        },
    },
    {
        "ref": "RelationType:rejects",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["rejects"],
            "updated_at": "2026-05-12T13:16:56.892000000+00:00",
            "confidence": 0.72,
            "label": "rejects",
            "created_by": "created_from_predicate",
            "key": "rejects",
        },
    },
    {
        "ref": "RelationType:replaces_purchase_of",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["replaces purchase of"],
            "updated_at": "2026-05-12T13:18:54.632000000+00:00",
            "confidence": 0.9,
            "label": "replaces purchase of",
            "created_by": "existing_similarity",
            "key": "replaces_purchase_of",
        },
    },
    {
        "ref": "RelationType:repurposed_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["repurposed_for"],
            "updated_at": "2026-05-12T13:19:32.286000000+00:00",
            "confidence": 0.72,
            "label": "repurposed_for",
            "created_by": "created_from_predicate",
            "key": "repurposed_for",
        },
    },
    {
        "ref": "RelationType:require",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["require"],
            "updated_at": "2026-05-12T13:20:56.494000000+00:00",
            "confidence": 0.9,
            "label": "require",
            "created_by": "existing_similarity",
            "key": "require",
        },
    },
    {
        "ref": "RelationType:scheduled_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["scheduled_for"],
            "updated_at": "2026-05-12T13:19:49.792000000+00:00",
            "confidence": 0.72,
            "label": "scheduled_for",
            "created_by": "created_from_predicate",
            "key": "scheduled_for",
        },
    },
    {
        "ref": "RelationType:secured_with",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["secured with"],
            "updated_at": "2026-05-12T13:18:54.597000000+00:00",
            "confidence": 0.72,
            "label": "secured with",
            "created_by": "created_from_predicate",
            "key": "secured_with",
        },
    },
    {
        "ref": "RelationType:selects",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["selects"],
            "updated_at": "2026-05-12T13:16:57.113000000+00:00",
            "confidence": 0.72,
            "label": "selects",
            "created_by": "created_from_predicate",
            "key": "selects",
        },
    },
    {
        "ref": "RelationType:should_be_documented_via",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["should be documented via"],
            "updated_at": "2026-05-12T13:20:26.282000000+00:00",
            "confidence": 0.72,
            "label": "should be documented via",
            "created_by": "created_from_predicate",
            "key": "should_be_documented_via",
        },
    },
    {
        "ref": "RelationType:should_be_evaluated_for",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["should be evaluated for"],
            "updated_at": "2026-05-12T13:20:26.252000000+00:00",
            "confidence": 0.72,
            "label": "should be evaluated for",
            "created_by": "created_from_predicate",
            "key": "should_be_evaluated_for",
        },
    },
    {
        "ref": "RelationType:should_segregate",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["should segregate"],
            "updated_at": "2026-05-12T13:20:26.033000000+00:00",
            "confidence": 0.72,
            "label": "should segregate",
            "created_by": "created_from_predicate",
            "key": "should_segregate",
        },
    },
    {
        "ref": "RelationType:tolerates",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["tolerates"],
            "updated_at": "2026-05-12T13:18:54.760000000+00:00",
            "confidence": 0.72,
            "label": "tolerates",
            "created_by": "created_from_predicate",
            "key": "tolerates",
        },
    },
    {
        "ref": "RelationType:wrapped_with",
        "labels": ["RelationType"],
        "props": {
            "aliases": ["wrapped with"],
            "updated_at": "2026-05-12T13:18:54.581000000+00:00",
            "confidence": 0.72,
            "label": "wrapped with",
            "created_by": "created_from_predicate",
            "key": "wrapped_with",
        },
    },
]

GRAPH_RELATIONSHIPS = [
    {
        "start": "ForumPost:4",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-4-v3-c0",
        "props": {},
    },
    {
        "start": "ForumPost:9",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-9-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:11",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-11-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:8",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-8-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:12",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-12-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:6",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-6-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:1",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-1-v3-c0",
        "props": {},
    },
    {
        "start": "ForumPost:3",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-3-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:7",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-7-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:5",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-5-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:2",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-2-v2-c0",
        "props": {},
    },
    {
        "start": "ForumPost:10",
        "type": "HAS_CHUNK",
        "end": "KnowledgeChunk:post-10-v2-c0",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-fd1508f2a092951630dc",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-9cc49078709c0bbe83b2",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-4338d1a98cd7523bfb46",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-7e2b31ffe495f7f8b6a9",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-c17e04775274afbca44d",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-c41c7cd06aee83d56291",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-3fd9ce5ebae2e41b6c22",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-dfb94e8f4a04968e9efe",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-228e851b2640da88f897",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-20419b91d26d9cd75c7a",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-f2a898b934440d547efd",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-87a159d48e1d517cd860",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-324a331faa753d9fd9ea",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-c798880471301f0b2423",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-4f0858a9aba66b1f6d4a",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-dc2a9817d735b152e991",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-81392ac5c162628330f5",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-f92e492ce435f8626de6",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-3e920eb430edee8050ca",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-70a1d717e109eeb320cd",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-e1839e9b577645272c10",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-17003b5804a9f4bcd6f0",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-36f97362e819d72b5fe6",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-a125183d312510a757a0",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-e9fc06beb86a8df34bbd",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-65ce9039b9a8f38b163c",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-4366ba9358dbc38e870c",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-f9fc4f597a1d720cd385",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-0a7a2b01de2b3a4c8c15",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-6f2283ac450218475788",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-2bdbcb9993bdb7da3870",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-2e9eaeeff7a42791490a",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-4748885f5ecbdb69f0e6",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-ea09ed210b63909cab62",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-6b956deae93fd003d888",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-f36072afe90ff168ad03",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-6d00d6c480959ccb58b3",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-47b3f70bc68cb2597798",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-5e6073daa8cc48e3e0d3",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-09c84fff162315a2f40b",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-3362c8088f9131c433d3",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-8bd2c561fc2a5133e0fb",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-62c8a6f9cd2d046364a1",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-90ce1e24293c3efc26db",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-dac139e1590581f31d92",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-9d83516342e2cd07ddad",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-a4986a2367d0ed03a459",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-8e0b0340a06f59c90afd",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-76f621a289570d6ce85b",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-5e8843f752deb6ad8146",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-99897f9a68a6949b1d02",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-455d31e095a2f52c5dde",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-34fcddb9609f33da510c",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-bbf72e6e54ed216fa4ea",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-6bff894449c8627cbe60",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-0871cf1fd09dc16773ac",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-a4dc373bbb84547ffb39",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-eb9462ee5e425ecd086e",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-4588a9d695ff9e43e689",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-170ee655f7da80bb32ec",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-30683ba114e0b9811a62",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-5c74eba56a0c56188b1d",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-363504b805f9bb8b6dcc",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-207f5f2d2dae675b0870",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "HAS_CLAIM",
        "end": "Claim:claim-247c389eb5ceb92a8dfd",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7aefc0c9c9593776348",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-c2f704b0212adece4f59",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-4f3d3ad6ec29f1103bba",
        "props": {},
    },
    {
        "start": "RelationFact:fact-29558dffbf760b96dad7",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-94b85e77381d5719bb06",
        "props": {},
    },
    {
        "start": "RelationFact:fact-de71ec0b6c56f799e56c",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-b6576d499c1d89b90d31",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9963222c51712162f9e0",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-c9e7256925da0bdb84e4",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8de82e9dc1dd367598d2",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-77551a38ea39e1f73dd9",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cc66c3b40366f651ab0f",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-d981d7ad623192580a4b",
        "props": {},
    },
    {
        "start": "RelationFact:fact-defbba56909591fcdaaa",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-1226d293c719a0d201cc",
        "props": {},
    },
    {
        "start": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-fd4520c535be33a82e0b",
        "props": {},
    },
    {
        "start": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-5b62461dd01fe92249b4",
        "props": {},
    },
    {
        "start": "RelationFact:fact-f2b6ee037bb9837292da",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-709bdede5bbf99ea8cb7",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-29af1598dd49db086af0",
        "props": {},
    },
    {
        "start": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-b245f8ccf212e780dd1a",
        "props": {},
    },
    {
        "start": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-482695c5d2b311cadb77",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-165347d7d10023a84336",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-304601b6d02f13d2594b",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8d603e53dfdca6798ca8",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-283049beb78a0fd66db7",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-95c87502bff0e4a86ab3",
        "props": {},
    },
    {
        "start": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-13a05c17a49eba877729",
        "props": {},
    },
    {
        "start": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-3b12e45bda1ce087ba77",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-57cded6e886f40df3aee",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0547469d9c71745dcc57",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-2b5441320dd432a89bc7",
        "props": {},
    },
    {
        "start": "RelationFact:fact-84cae26b50128796d354",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-4595106c82cde7df0cac",
        "props": {},
    },
    {
        "start": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-40e48eb38a6259af85ef",
        "props": {},
    },
    {
        "start": "RelationFact:fact-13ff9e845580d253cfec",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-ef40ce24f0d8b91cc286",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4729b75726640103591d",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-893b723b585cc0aadc26",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2223962ae695cf302f32",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-ccc97b270e6a5c8742b4",
        "props": {},
    },
    {
        "start": "RelationFact:fact-22f8a37933bc642bf853",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-2d032b2634b46e067677",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-f15b5140fbacb473a82c",
        "props": {},
    },
    {
        "start": "RelationFact:fact-05e5356d27d8ed09be12",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-22cce2e85458548451f1",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8beb84f279311656bef1",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-74b4625bbae9b5a3e619",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c30d4f82e7b4912c5446",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-bee9fe241199a4299770",
        "props": {},
    },
    {
        "start": "RelationFact:fact-bd130e3440285e314333",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-647cb29b85d7c3d64837",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0042790fc1e238c472af",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-8cb9cd95176667765194",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-b5af06345f7b7d41d357",
        "props": {},
    },
    {
        "start": "RelationFact:fact-e0e8da778fcefd0b8873",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-b8b8a1e3609c20411bb0",
        "props": {},
    },
    {
        "start": "RelationFact:fact-aa4483d4fc5be4197267",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-ec1f2e3e220ff01b2890",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7333437cb5932c1a0d6f",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-3a4df5b0e29e1b55f56a",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7079f73f8eb5c487730",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-1ca4ec35064bacf013cb",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cca25498c9babd07a929",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-5dee65001425be0b1998",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4b167573656803ef312c",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-e7bf35187ecfa3ca0e53",
        "props": {},
    },
    {
        "start": "RelationFact:fact-19f82c23ed2794c48e62",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-9ad7559148c8dedd6630",
        "props": {},
    },
    {
        "start": "RelationFact:fact-194edfd0054ea27e3d98",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-686dd283887852553607",
        "props": {},
    },
    {
        "start": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-c2a893674e4ac459ffec",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9eab4dea6c51e2066546",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-1f7a5871d1852c509a43",
        "props": {},
    },
    {
        "start": "RelationFact:fact-094ce29c13c649beb84e",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-507e77e6876017b80d99",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c903d0168876dbb8ba96",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-8eb122ed9756ad46fa63",
        "props": {},
    },
    {
        "start": "RelationFact:fact-60975c819ea80a37a2e7",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-1882f0b12bab2f949fd5",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-32b77ba1680f8757199e",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef2bed229e62219b456a",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-1af11d29eee64d056dcb",
        "props": {},
    },
    {
        "start": "RelationFact:fact-daf9403c2d40902e8fbe",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-d6a23f91cc54a1fb93a9",
        "props": {},
    },
    {
        "start": "RelationFact:fact-576a33c4db476e2b60d4",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-a4ba8d0794980cea9a15",
        "props": {},
    },
    {
        "start": "RelationFact:fact-49c91518b55a5cddc2b5",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-824a03a7de6795b01432",
        "props": {},
    },
    {
        "start": "RelationFact:fact-458add0bdec4a9a8165d",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-2fb7462b5de5605a8d90",
        "props": {},
    },
    {
        "start": "RelationFact:fact-546d15efb08e221cf2dd",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-2da743881c28da58a96e",
        "props": {},
    },
    {
        "start": "RelationFact:fact-755576d6ba38127cb4a6",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-b5fa747a066f3cb35354",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-c2fc3650c84e3cae6841",
        "props": {},
    },
    {
        "start": "RelationFact:fact-69248e4b2a5afb0db0df",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-16aa4be77f122010ce74",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-98535c71241e6abf3b59",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-7e1c17ff3b0a66302433",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7a274e626c596c992df5",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-77c3544d8f41bf67e128",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3026d76c11729aa75d75",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-9d06ba81655e5306b196",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-6059d2519be12b3b9c87",
        "props": {},
    },
    {
        "start": "RelationFact:fact-50d5618b306780063992",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-dcc643d5f163a57b276e",
        "props": {},
    },
    {
        "start": "RelationFact:fact-d7e611f93698ff7506ae",
        "type": "HAS_EVIDENCE",
        "end": "Evidence:evidence-ac979bb6be6ebe73c866",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:coffee_tin",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:utensil_holder",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:adhesive_paper",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:kitchen_countertop",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:cooking_utensils",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-4-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:kitchen_containers",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:paper_bag",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:drawer_divider",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:kitchen_drawer",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:zero_cost_hack",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:commercial_organizer",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-9-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:long_term_storage",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:disposable_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:remote_controls",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:flashlight",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:wireless_mouse",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-11-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:battery_waste",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:decorative_storage_boxes",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:acrylic_organizers",
        "props": {},
    },
    {"start": "KnowledgeChunk:post-8-v2-c0", "type": "MENTIONS", "end": "Entity:jars", "props": {}},
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:trays",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:laundry_basket",
        "props": {},
    },
    {"start": "KnowledgeChunk:post-8-v2-c0", "type": "MENTIONS", "end": "Entity:tote", "props": {}},
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:desk_lamp",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:impulse_purchases",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:dorm_room",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-8-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:surfaces",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:sorting_labels",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:recycling_bins",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:household_recycling",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-12-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:kitchen",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:desk_drawer",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:e_waste",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:power_bank",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:keyboard",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:category_check",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:drop_off",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:tech_drawer_reset",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:non_waste_items",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:responsible_recycling",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:disposal_options",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-6-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:cleaning",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:aluminum_can",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:pen_holder",
        "props": {},
    },
    {"start": "KnowledgeChunk:post-1-v3-c0", "type": "MENTIONS", "end": "Entity:desk", "props": {}},
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:paper_wrap",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:loose_stationery",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:cut_edge",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:sticky_residue",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:matching_pair",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:visual_balance",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:sanding",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:intentional_aesthetic",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-1-v3-c0",
        "type": "MENTIONS",
        "end": "Entity:immediate_washing",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:cardboard_mailer",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:kraft_paper",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:double_sided_tape",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:ribbon",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:dried_flower_tag",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:gift_box",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:upcycling",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:new_packaging",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-3-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:imperfect_execution",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:glass_jars",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:spice_shelf",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:kitchen",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:consistent_labeling",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:packaging_waste",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:duplicate_purchases",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-7-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:inventory_tracking",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:cleanup_session",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:saturday",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:recyclables",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:riverside_path",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:litter",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-5-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:cleaning_supplies",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:aa_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:aaa_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:button_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:lithium_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:electrical_tape",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:battery_recycling",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:drop_off_locations",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:storage_containers",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:used_batteries",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:remaining_functionality",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:pre_sorted_organization",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-2-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:digital_notes",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:plastic_bottle",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:diy_lantern",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:national_day",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:led_light",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:handmade_appearance",
        "props": {},
    },
    {
        "start": "KnowledgeChunk:post-10-v2-c0",
        "type": "MENTIONS",
        "end": "Entity:festive_craft_reuse",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7aefc0c9c9593776348",
        "type": "OBJECT",
        "end": "Entity:utensil_holder",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "type": "OBJECT",
        "end": "Entity:coffee_tin",
        "props": {},
    },
    {
        "start": "RelationFact:fact-29558dffbf760b96dad7",
        "type": "OBJECT",
        "end": "Entity:kitchen_countertop",
        "props": {},
    },
    {
        "start": "RelationFact:fact-de71ec0b6c56f799e56c",
        "type": "OBJECT",
        "end": "Entity:kitchen_containers",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9963222c51712162f9e0",
        "type": "OBJECT",
        "end": "Entity:drawer_divider",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8de82e9dc1dd367598d2",
        "type": "OBJECT",
        "end": "Entity:kitchen_drawer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cc66c3b40366f651ab0f",
        "type": "OBJECT",
        "end": "Entity:kitchen_drawer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-defbba56909591fcdaaa",
        "type": "OBJECT",
        "end": "Entity:long_term_storage",
        "props": {},
    },
    {
        "start": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "type": "OBJECT",
        "end": "Entity:zero_cost_hack",
        "props": {},
    },
    {
        "start": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "type": "OBJECT",
        "end": "Entity:disposable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-f2b6ee037bb9837292da",
        "type": "OBJECT",
        "end": "Entity:battery_waste",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "type": "OBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "type": "OBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "type": "OBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "type": "OBJECT",
        "end": "Entity:decorative_storage_boxes",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "type": "OBJECT",
        "end": "Entity:acrylic_organizers",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8d603e53dfdca6798ca8",
        "type": "OBJECT",
        "end": "Entity:jars",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "type": "OBJECT",
        "end": "Entity:tote",
        "props": {},
    },
    {
        "start": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "type": "OBJECT",
        "end": "Entity:surfaces",
        "props": {},
    },
    {
        "start": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "type": "OBJECT",
        "end": "Entity:impulse_purchases",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "type": "OBJECT",
        "end": "Entity:desk_lamp",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0547469d9c71745dcc57",
        "type": "OBJECT",
        "end": "Entity:dorm_room",
        "props": {},
    },
    {
        "start": "RelationFact:fact-84cae26b50128796d354",
        "type": "OBJECT",
        "end": "Entity:household_recycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "type": "OBJECT",
        "end": "Entity:sorting_labels",
        "props": {},
    },
    {
        "start": "RelationFact:fact-13ff9e845580d253cfec",
        "type": "OBJECT",
        "end": "Entity:kitchen",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4729b75726640103591d",
        "type": "OBJECT",
        "end": "Entity:recycling_bins",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2223962ae695cf302f32",
        "type": "OBJECT",
        "end": "Entity:recycling_bins",
        "props": {},
    },
    {
        "start": "RelationFact:fact-22f8a37933bc642bf853",
        "type": "OBJECT",
        "end": "Entity:e_waste",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "type": "OBJECT",
        "end": "Entity:non_waste_items",
        "props": {},
    },
    {
        "start": "RelationFact:fact-05e5356d27d8ed09be12",
        "type": "OBJECT",
        "end": "Entity:responsible_recycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8beb84f279311656bef1",
        "type": "OBJECT",
        "end": "Entity:cleaning",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c30d4f82e7b4912c5446",
        "type": "OBJECT",
        "end": "Entity:drop_off",
        "props": {},
    },
    {
        "start": "RelationFact:fact-bd130e3440285e314333",
        "type": "OBJECT",
        "end": "Entity:disposal_options",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0042790fc1e238c472af",
        "type": "OBJECT",
        "end": "Entity:pen_holder",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "type": "OBJECT",
        "end": "Entity:loose_stationery",
        "props": {},
    },
    {
        "start": "RelationFact:fact-e0e8da778fcefd0b8873",
        "type": "OBJECT",
        "end": "Entity:sanding",
        "props": {},
    },
    {
        "start": "RelationFact:fact-aa4483d4fc5be4197267",
        "type": "OBJECT",
        "end": "Entity:intentional_aesthetic",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7333437cb5932c1a0d6f",
        "type": "OBJECT",
        "end": "Entity:immediate_washing",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7079f73f8eb5c487730",
        "type": "OBJECT",
        "end": "Entity:visual_balance",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cca25498c9babd07a929",
        "type": "OBJECT",
        "end": "Entity:gift_box",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4b167573656803ef312c",
        "type": "OBJECT",
        "end": "Entity:kraft_paper",
        "props": {},
    },
    {
        "start": "RelationFact:fact-19f82c23ed2794c48e62",
        "type": "OBJECT",
        "end": "Entity:double_sided_tape",
        "props": {},
    },
    {
        "start": "RelationFact:fact-194edfd0054ea27e3d98",
        "type": "OBJECT",
        "end": "Entity:ribbon",
        "props": {},
    },
    {
        "start": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "type": "OBJECT",
        "end": "Entity:new_packaging",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9eab4dea6c51e2066546",
        "type": "OBJECT",
        "end": "Entity:imperfect_execution",
        "props": {},
    },
    {
        "start": "RelationFact:fact-094ce29c13c649beb84e",
        "type": "OBJECT",
        "end": "Entity:spice_shelf",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c903d0168876dbb8ba96",
        "type": "OBJECT",
        "end": "Entity:kitchen",
        "props": {},
    },
    {
        "start": "RelationFact:fact-60975c819ea80a37a2e7",
        "type": "OBJECT",
        "end": "Entity:duplicate_purchases",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "type": "OBJECT",
        "end": "Entity:packaging_waste",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef2bed229e62219b456a",
        "type": "OBJECT",
        "end": "Entity:inventory_tracking",
        "props": {},
    },
    {
        "start": "RelationFact:fact-daf9403c2d40902e8fbe",
        "type": "OBJECT",
        "end": "Entity:saturday",
        "props": {},
    },
    {
        "start": "RelationFact:fact-576a33c4db476e2b60d4",
        "type": "OBJECT",
        "end": "Entity:recyclables",
        "props": {},
    },
    {
        "start": "RelationFact:fact-49c91518b55a5cddc2b5",
        "type": "OBJECT",
        "end": "Entity:litter",
        "props": {},
    },
    {
        "start": "RelationFact:fact-458add0bdec4a9a8165d",
        "type": "OBJECT",
        "end": "Entity:cleaning_supplies",
        "props": {},
    },
    {
        "start": "RelationFact:fact-546d15efb08e221cf2dd",
        "type": "OBJECT",
        "end": "Entity:aa_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-755576d6ba38127cb4a6",
        "type": "OBJECT",
        "end": "Entity:electrical_tape",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "type": "OBJECT",
        "end": "Entity:electrical_tape",
        "props": {},
    },
    {
        "start": "RelationFact:fact-69248e4b2a5afb0db0df",
        "type": "OBJECT",
        "end": "Entity:remaining_functionality",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "type": "OBJECT",
        "end": "Entity:pre_sorted_organization",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "type": "OBJECT",
        "end": "Entity:digital_notes",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7a274e626c596c992df5",
        "type": "OBJECT",
        "end": "Entity:diy_lantern",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3026d76c11729aa75d75",
        "type": "OBJECT",
        "end": "Entity:national_day",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "type": "OBJECT",
        "end": "Entity:led_light",
        "props": {},
    },
    {
        "start": "RelationFact:fact-50d5618b306780063992",
        "type": "OBJECT",
        "end": "Entity:handmade_appearance",
        "props": {},
    },
    {
        "start": "RelationFact:fact-d7e611f93698ff7506ae",
        "type": "OBJECT",
        "end": "Entity:festive_craft_reuse",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7aefc0c9c9593776348",
        "type": "SUBJECT",
        "end": "Entity:coffee_tin",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "type": "SUBJECT",
        "end": "Entity:adhesive_paper",
        "props": {},
    },
    {
        "start": "RelationFact:fact-29558dffbf760b96dad7",
        "type": "SUBJECT",
        "end": "Entity:utensil_holder",
        "props": {},
    },
    {
        "start": "RelationFact:fact-de71ec0b6c56f799e56c",
        "type": "SUBJECT",
        "end": "Entity:coffee_tin",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9963222c51712162f9e0",
        "type": "SUBJECT",
        "end": "Entity:paper_bag",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8de82e9dc1dd367598d2",
        "type": "SUBJECT",
        "end": "Entity:drawer_divider",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cc66c3b40366f651ab0f",
        "type": "SUBJECT",
        "end": "Entity:zero_cost_hack",
        "props": {},
    },
    {
        "start": "RelationFact:fact-defbba56909591fcdaaa",
        "type": "SUBJECT",
        "end": "Entity:drawer_divider",
        "props": {},
    },
    {
        "start": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "type": "SUBJECT",
        "end": "Entity:commercial_organizer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "type": "SUBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-f2b6ee037bb9837292da",
        "type": "SUBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "type": "SUBJECT",
        "end": "Entity:remote_controls",
        "props": {},
    },
    {
        "start": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "type": "SUBJECT",
        "end": "Entity:flashlight",
        "props": {},
    },
    {
        "start": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "type": "SUBJECT",
        "end": "Entity:wireless_mouse",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8d603e53dfdca6798ca8",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0547469d9c71745dcc57",
        "type": "SUBJECT",
        "end": "Entity:low_buy_approach",
        "props": {},
    },
    {
        "start": "RelationFact:fact-84cae26b50128796d354",
        "type": "SUBJECT",
        "end": "Entity:sorting_labels",
        "props": {},
    },
    {
        "start": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "type": "SUBJECT",
        "end": "Entity:recycling_bins",
        "props": {},
    },
    {
        "start": "RelationFact:fact-13ff9e845580d253cfec",
        "type": "SUBJECT",
        "end": "Entity:household_recycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4729b75726640103591d",
        "type": "SUBJECT",
        "end": "Entity:sorting_labels",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2223962ae695cf302f32",
        "type": "SUBJECT",
        "end": "Entity:household_recycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-22f8a37933bc642bf853",
        "type": "SUBJECT",
        "end": "Entity:desk_drawer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "type": "SUBJECT",
        "end": "Entity:e_waste",
        "props": {},
    },
    {
        "start": "RelationFact:fact-05e5356d27d8ed09be12",
        "type": "SUBJECT",
        "end": "Entity:power_bank",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8beb84f279311656bef1",
        "type": "SUBJECT",
        "end": "Entity:keyboard",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c30d4f82e7b4912c5446",
        "type": "SUBJECT",
        "end": "Entity:category_check",
        "props": {},
    },
    {
        "start": "RelationFact:fact-bd130e3440285e314333",
        "type": "SUBJECT",
        "end": "Entity:tech_drawer_reset",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0042790fc1e238c472af",
        "type": "SUBJECT",
        "end": "Entity:aluminum_can",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "type": "SUBJECT",
        "end": "Entity:pen_holder",
        "props": {},
    },
    {
        "start": "RelationFact:fact-e0e8da778fcefd0b8873",
        "type": "SUBJECT",
        "end": "Entity:cut_edge",
        "props": {},
    },
    {
        "start": "RelationFact:fact-aa4483d4fc5be4197267",
        "type": "SUBJECT",
        "end": "Entity:paper_wrap",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7333437cb5932c1a0d6f",
        "type": "SUBJECT",
        "end": "Entity:sticky_residue",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7079f73f8eb5c487730",
        "type": "SUBJECT",
        "end": "Entity:matching_pair",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cca25498c9babd07a929",
        "type": "SUBJECT",
        "end": "Entity:cardboard_mailer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4b167573656803ef312c",
        "type": "SUBJECT",
        "end": "Entity:cardboard_mailer",
        "props": {},
    },
    {
        "start": "RelationFact:fact-19f82c23ed2794c48e62",
        "type": "SUBJECT",
        "end": "Entity:kraft_paper",
        "props": {},
    },
    {
        "start": "RelationFact:fact-194edfd0054ea27e3d98",
        "type": "SUBJECT",
        "end": "Entity:gift_box",
        "props": {},
    },
    {
        "start": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "type": "SUBJECT",
        "end": "Entity:upcycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9eab4dea6c51e2066546",
        "type": "SUBJECT",
        "end": "Entity:upcycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-094ce29c13c649beb84e",
        "type": "SUBJECT",
        "end": "Entity:glass_jars",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c903d0168876dbb8ba96",
        "type": "SUBJECT",
        "end": "Entity:spice_shelf",
        "props": {},
    },
    {
        "start": "RelationFact:fact-60975c819ea80a37a2e7",
        "type": "SUBJECT",
        "end": "Entity:consistent_labeling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "type": "SUBJECT",
        "end": "Entity:glass_jars",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef2bed229e62219b456a",
        "type": "SUBJECT",
        "end": "Entity:consistent_labeling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-daf9403c2d40902e8fbe",
        "type": "SUBJECT",
        "end": "Entity:cleanup_session",
        "props": {},
    },
    {
        "start": "RelationFact:fact-576a33c4db476e2b60d4",
        "type": "SUBJECT",
        "end": "Entity:cleanup_session",
        "props": {},
    },
    {
        "start": "RelationFact:fact-49c91518b55a5cddc2b5",
        "type": "SUBJECT",
        "end": "Entity:riverside_path",
        "props": {},
    },
    {
        "start": "RelationFact:fact-458add0bdec4a9a8165d",
        "type": "SUBJECT",
        "end": "Entity:cleanup_session",
        "props": {},
    },
    {
        "start": "RelationFact:fact-546d15efb08e221cf2dd",
        "type": "SUBJECT",
        "end": "Entity:storage_containers",
        "props": {},
    },
    {
        "start": "RelationFact:fact-755576d6ba38127cb4a6",
        "type": "SUBJECT",
        "end": "Entity:lithium_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "type": "SUBJECT",
        "end": "Entity:rechargeable_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-69248e4b2a5afb0db0df",
        "type": "SUBJECT",
        "end": "Entity:used_batteries",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "type": "SUBJECT",
        "end": "Entity:battery_recycling",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "type": "SUBJECT",
        "end": "Entity:drop_off_locations",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7a274e626c596c992df5",
        "type": "SUBJECT",
        "end": "Entity:plastic_bottle",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3026d76c11729aa75d75",
        "type": "SUBJECT",
        "end": "Entity:diy_lantern",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "type": "SUBJECT",
        "end": "Entity:diy_lantern",
        "props": {},
    },
    {
        "start": "RelationFact:fact-50d5618b306780063992",
        "type": "SUBJECT",
        "end": "Entity:diy_lantern",
        "props": {},
    },
    {
        "start": "RelationFact:fact-d7e611f93698ff7506ae",
        "type": "SUBJECT",
        "end": "Entity:plastic_bottle",
        "props": {},
    },
    {
        "start": "Claim:claim-fd1508f2a092951630dc",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-a7aefc0c9c9593776348",
        "props": {},
    },
    {
        "start": "Claim:claim-9cc49078709c0bbe83b2",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "props": {},
    },
    {
        "start": "Claim:claim-4338d1a98cd7523bfb46",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-29558dffbf760b96dad7",
        "props": {},
    },
    {
        "start": "Claim:claim-7e2b31ffe495f7f8b6a9",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-de71ec0b6c56f799e56c",
        "props": {},
    },
    {
        "start": "Claim:claim-c17e04775274afbca44d",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-9963222c51712162f9e0",
        "props": {},
    },
    {
        "start": "Claim:claim-c41c7cd06aee83d56291",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-8de82e9dc1dd367598d2",
        "props": {},
    },
    {
        "start": "Claim:claim-3fd9ce5ebae2e41b6c22",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-cc66c3b40366f651ab0f",
        "props": {},
    },
    {
        "start": "Claim:claim-dfb94e8f4a04968e9efe",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-defbba56909591fcdaaa",
        "props": {},
    },
    {
        "start": "Claim:claim-228e851b2640da88f897",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "props": {},
    },
    {
        "start": "Claim:claim-20419b91d26d9cd75c7a",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "props": {},
    },
    {
        "start": "Claim:claim-f2a898b934440d547efd",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-f2b6ee037bb9837292da",
        "props": {},
    },
    {
        "start": "Claim:claim-87a159d48e1d517cd860",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "props": {},
    },
    {
        "start": "Claim:claim-324a331faa753d9fd9ea",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "props": {},
    },
    {
        "start": "Claim:claim-c798880471301f0b2423",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "props": {},
    },
    {
        "start": "Claim:claim-4f0858a9aba66b1f6d4a",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "props": {},
    },
    {
        "start": "Claim:claim-dc2a9817d735b152e991",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "props": {},
    },
    {
        "start": "Claim:claim-81392ac5c162628330f5",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-8d603e53dfdca6798ca8",
        "props": {},
    },
    {
        "start": "Claim:claim-f92e492ce435f8626de6",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "props": {},
    },
    {
        "start": "Claim:claim-3e920eb430edee8050ca",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "props": {},
    },
    {
        "start": "Claim:claim-70a1d717e109eeb320cd",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "props": {},
    },
    {
        "start": "Claim:claim-e1839e9b577645272c10",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "props": {},
    },
    {
        "start": "Claim:claim-17003b5804a9f4bcd6f0",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-0547469d9c71745dcc57",
        "props": {},
    },
    {
        "start": "Claim:claim-36f97362e819d72b5fe6",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-84cae26b50128796d354",
        "props": {},
    },
    {
        "start": "Claim:claim-a125183d312510a757a0",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "props": {},
    },
    {
        "start": "Claim:claim-e9fc06beb86a8df34bbd",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-13ff9e845580d253cfec",
        "props": {},
    },
    {
        "start": "Claim:claim-65ce9039b9a8f38b163c",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-4729b75726640103591d",
        "props": {},
    },
    {
        "start": "Claim:claim-4366ba9358dbc38e870c",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-2223962ae695cf302f32",
        "props": {},
    },
    {
        "start": "Claim:claim-f9fc4f597a1d720cd385",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-22f8a37933bc642bf853",
        "props": {},
    },
    {
        "start": "Claim:claim-0a7a2b01de2b3a4c8c15",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "props": {},
    },
    {
        "start": "Claim:claim-6f2283ac450218475788",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-05e5356d27d8ed09be12",
        "props": {},
    },
    {
        "start": "Claim:claim-2bdbcb9993bdb7da3870",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-8beb84f279311656bef1",
        "props": {},
    },
    {
        "start": "Claim:claim-2e9eaeeff7a42791490a",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-c30d4f82e7b4912c5446",
        "props": {},
    },
    {
        "start": "Claim:claim-4748885f5ecbdb69f0e6",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-bd130e3440285e314333",
        "props": {},
    },
    {
        "start": "Claim:claim-ea09ed210b63909cab62",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-0042790fc1e238c472af",
        "props": {},
    },
    {
        "start": "Claim:claim-6b956deae93fd003d888",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "props": {},
    },
    {
        "start": "Claim:claim-f36072afe90ff168ad03",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-e0e8da778fcefd0b8873",
        "props": {},
    },
    {
        "start": "Claim:claim-6d00d6c480959ccb58b3",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-aa4483d4fc5be4197267",
        "props": {},
    },
    {
        "start": "Claim:claim-47b3f70bc68cb2597798",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-7333437cb5932c1a0d6f",
        "props": {},
    },
    {
        "start": "Claim:claim-5e6073daa8cc48e3e0d3",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-a7079f73f8eb5c487730",
        "props": {},
    },
    {
        "start": "Claim:claim-09c84fff162315a2f40b",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-cca25498c9babd07a929",
        "props": {},
    },
    {
        "start": "Claim:claim-3362c8088f9131c433d3",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-4b167573656803ef312c",
        "props": {},
    },
    {
        "start": "Claim:claim-8bd2c561fc2a5133e0fb",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-19f82c23ed2794c48e62",
        "props": {},
    },
    {
        "start": "Claim:claim-62c8a6f9cd2d046364a1",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-194edfd0054ea27e3d98",
        "props": {},
    },
    {
        "start": "Claim:claim-90ce1e24293c3efc26db",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "props": {},
    },
    {
        "start": "Claim:claim-dac139e1590581f31d92",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-9eab4dea6c51e2066546",
        "props": {},
    },
    {
        "start": "Claim:claim-9d83516342e2cd07ddad",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-094ce29c13c649beb84e",
        "props": {},
    },
    {
        "start": "Claim:claim-a4986a2367d0ed03a459",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-c903d0168876dbb8ba96",
        "props": {},
    },
    {
        "start": "Claim:claim-8e0b0340a06f59c90afd",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-60975c819ea80a37a2e7",
        "props": {},
    },
    {
        "start": "Claim:claim-76f621a289570d6ce85b",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "props": {},
    },
    {
        "start": "Claim:claim-5e8843f752deb6ad8146",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-ef2bed229e62219b456a",
        "props": {},
    },
    {
        "start": "Claim:claim-99897f9a68a6949b1d02",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-daf9403c2d40902e8fbe",
        "props": {},
    },
    {
        "start": "Claim:claim-455d31e095a2f52c5dde",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-576a33c4db476e2b60d4",
        "props": {},
    },
    {
        "start": "Claim:claim-34fcddb9609f33da510c",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-49c91518b55a5cddc2b5",
        "props": {},
    },
    {
        "start": "Claim:claim-bbf72e6e54ed216fa4ea",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-458add0bdec4a9a8165d",
        "props": {},
    },
    {
        "start": "Claim:claim-6bff894449c8627cbe60",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-546d15efb08e221cf2dd",
        "props": {},
    },
    {
        "start": "Claim:claim-0871cf1fd09dc16773ac",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-755576d6ba38127cb4a6",
        "props": {},
    },
    {
        "start": "Claim:claim-a4dc373bbb84547ffb39",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "props": {},
    },
    {
        "start": "Claim:claim-eb9462ee5e425ecd086e",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-69248e4b2a5afb0db0df",
        "props": {},
    },
    {
        "start": "Claim:claim-4588a9d695ff9e43e689",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "props": {},
    },
    {
        "start": "Claim:claim-170ee655f7da80bb32ec",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "props": {},
    },
    {
        "start": "Claim:claim-30683ba114e0b9811a62",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-7a274e626c596c992df5",
        "props": {},
    },
    {
        "start": "Claim:claim-5c74eba56a0c56188b1d",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-3026d76c11729aa75d75",
        "props": {},
    },
    {
        "start": "Claim:claim-363504b805f9bb8b6dcc",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "props": {},
    },
    {
        "start": "Claim:claim-207f5f2d2dae675b0870",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-50d5618b306780063992",
        "props": {},
    },
    {
        "start": "Claim:claim-247c389eb5ceb92a8dfd",
        "type": "SUPPORTS",
        "end": "RelationFact:fact-d7e611f93698ff7506ae",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7aefc0c9c9593776348",
        "type": "USES_RELATION",
        "end": "RelationType:can_be_reused_as",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c09c61b0de8ffa1a575b",
        "type": "USES_RELATION",
        "end": "RelationType:applied_to_exterior_of",
        "props": {},
    },
    {
        "start": "RelationFact:fact-29558dffbf760b96dad7",
        "type": "USES_RELATION",
        "end": "RelationType:organizes_on",
        "props": {},
    },
    {
        "start": "RelationFact:fact-de71ec0b6c56f799e56c",
        "type": "USES_RELATION",
        "end": "RelationType:replaces_purchase_of",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9963222c51712162f9e0",
        "type": "USES_RELATION",
        "end": "RelationType:can_be_reused_as",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8de82e9dc1dd367598d2",
        "type": "USES_RELATION",
        "end": "RelationType:reduces_visual_clutter_in",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cc66c3b40366f651ab0f",
        "type": "USES_RELATION",
        "end": "RelationType:provides_accessible_solution_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-defbba56909591fcdaaa",
        "type": "USES_RELATION",
        "end": "RelationType:has",
        "props": {},
    },
    {
        "start": "RelationFact:fact-b665d8dcdb5c06ca24cd",
        "type": "USES_RELATION",
        "end": "RelationType:is_unnecessary_replacement_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-5b2b8f860e311e95f5bb",
        "type": "USES_RELATION",
        "end": "RelationType:replaces_purchase_of",
        "props": {},
    },
    {
        "start": "RelationFact:fact-f2b6ee037bb9837292da",
        "type": "USES_RELATION",
        "end": "RelationType:reduces_visual_clutter_in",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c0b37ff31e6db0ca7b84",
        "type": "USES_RELATION",
        "end": "RelationType:compatible_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-74ac803fbdf31b9d39ac",
        "type": "USES_RELATION",
        "end": "RelationType:compatible_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-81d7a259bb01fffe7bfe",
        "type": "USES_RELATION",
        "end": "RelationType:compatible_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fc25f6300d71d4c93fa9",
        "type": "USES_RELATION",
        "end": "RelationType:has",
        "props": {},
    },
    {
        "start": "RelationFact:fact-fdc0a1d45319d8a4e238",
        "type": "USES_RELATION",
        "end": "RelationType:rejects",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8d603e53dfdca6798ca8",
        "type": "USES_RELATION",
        "end": "RelationType:can_be_reused_as",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a9fbcbbad7d7e2cd2337",
        "type": "USES_RELATION",
        "end": "RelationType:selects",
        "props": {},
    },
    {
        "start": "RelationFact:fact-33c46aec0bd9ccc1bec9",
        "type": "USES_RELATION",
        "end": "RelationType:keeps_clear",
        "props": {},
    },
    {
        "start": "RelationFact:fact-848a6c48d1d01f2e92f2",
        "type": "USES_RELATION",
        "end": "RelationType:filters",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2e4a8e8fbe178670a5fc",
        "type": "USES_RELATION",
        "end": "RelationType:borrows",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0547469d9c71745dcc57",
        "type": "USES_RELATION",
        "end": "RelationType:enhances",
        "props": {},
    },
    {
        "start": "RelationFact:fact-84cae26b50128796d354",
        "type": "USES_RELATION",
        "end": "RelationType:improve",
        "props": {},
    },
    {
        "start": "RelationFact:fact-62430e7f1d9b6d31b41f",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-13ff9e845580d253cfec",
        "type": "USES_RELATION",
        "end": "RelationType:reduce_friction_in",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4729b75726640103591d",
        "type": "USES_RELATION",
        "end": "RelationType:provide_instructions_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-2223962ae695cf302f32",
        "type": "USES_RELATION",
        "end": "RelationType:prioritize",
        "props": {},
    },
    {
        "start": "RelationFact:fact-22f8a37933bc642bf853",
        "type": "USES_RELATION",
        "end": "RelationType:accumulates",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9ed4387cd0a85b3b6b09",
        "type": "USES_RELATION",
        "end": "RelationType:has",
        "props": {},
    },
    {
        "start": "RelationFact:fact-05e5356d27d8ed09be12",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-8beb84f279311656bef1",
        "type": "USES_RELATION",
        "end": "RelationType:may_only_need",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c30d4f82e7b4912c5446",
        "type": "USES_RELATION",
        "end": "RelationType:reduces_waste_during",
        "props": {},
    },
    {
        "start": "RelationFact:fact-bd130e3440285e314333",
        "type": "USES_RELATION",
        "end": "RelationType:identifies",
        "props": {},
    },
    {
        "start": "RelationFact:fact-0042790fc1e238c472af",
        "type": "USES_RELATION",
        "end": "RelationType:can_be_reused_as",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef45dc619e1e8ac9048a",
        "type": "USES_RELATION",
        "end": "RelationType:is_recommended_for_storing",
        "props": {},
    },
    {
        "start": "RelationFact:fact-e0e8da778fcefd0b8873",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-aa4483d4fc5be4197267",
        "type": "USES_RELATION",
        "end": "RelationType:provides_accessible_solution_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7333437cb5932c1a0d6f",
        "type": "USES_RELATION",
        "end": "RelationType:is_avoided_by",
        "props": {},
    },
    {
        "start": "RelationFact:fact-a7079f73f8eb5c487730",
        "type": "USES_RELATION",
        "end": "RelationType:enhances",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cca25498c9babd07a929",
        "type": "USES_RELATION",
        "end": "RelationType:can_be_reused_as",
        "props": {},
    },
    {
        "start": "RelationFact:fact-4b167573656803ef312c",
        "type": "USES_RELATION",
        "end": "RelationType:wrapped_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-19f82c23ed2794c48e62",
        "type": "USES_RELATION",
        "end": "RelationType:secured_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-194edfd0054ea27e3d98",
        "type": "USES_RELATION",
        "end": "RelationType:decorated_with",
        "props": {},
    },
    {
        "start": "RelationFact:fact-6dba8a8c2dfa70cdcffc",
        "type": "USES_RELATION",
        "end": "RelationType:replaces_purchase_of",
        "props": {},
    },
    {
        "start": "RelationFact:fact-9eab4dea6c51e2066546",
        "type": "USES_RELATION",
        "end": "RelationType:tolerates",
        "props": {},
    },
    {
        "start": "RelationFact:fact-094ce29c13c649beb84e",
        "type": "USES_RELATION",
        "end": "RelationType:repurposed_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-c903d0168876dbb8ba96",
        "type": "USES_RELATION",
        "end": "RelationType:improve",
        "props": {},
    },
    {
        "start": "RelationFact:fact-60975c819ea80a37a2e7",
        "type": "USES_RELATION",
        "end": "RelationType:minimizes",
        "props": {},
    },
    {
        "start": "RelationFact:fact-cef84f8f3c4769fe08b4",
        "type": "USES_RELATION",
        "end": "RelationType:eliminates_concern_about",
        "props": {},
    },
    {
        "start": "RelationFact:fact-ef2bed229e62219b456a",
        "type": "USES_RELATION",
        "end": "RelationType:enables",
        "props": {},
    },
    {
        "start": "RelationFact:fact-daf9403c2d40902e8fbe",
        "type": "USES_RELATION",
        "end": "RelationType:scheduled_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-576a33c4db476e2b60d4",
        "type": "USES_RELATION",
        "end": "RelationType:aims_to_separate",
        "props": {},
    },
    {
        "start": "RelationFact:fact-49c91518b55a5cddc2b5",
        "type": "USES_RELATION",
        "end": "RelationType:accumulates",
        "props": {},
    },
    {
        "start": "RelationFact:fact-458add0bdec4a9a8165d",
        "type": "USES_RELATION",
        "end": "RelationType:provides_accessible_solution_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-546d15efb08e221cf2dd",
        "type": "USES_RELATION",
        "end": "RelationType:should_segregate",
        "props": {},
    },
    {
        "start": "RelationFact:fact-755576d6ba38127cb4a6",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3c1ee445188ba98f6d5e",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-69248e4b2a5afb0db0df",
        "type": "USES_RELATION",
        "end": "RelationType:should_be_evaluated_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3cba1d4cb61f3a49a1a3",
        "type": "USES_RELATION",
        "end": "RelationType:is_expedited_by",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7ec76661b8608c0a0fe1",
        "type": "USES_RELATION",
        "end": "RelationType:should_be_documented_via",
        "props": {},
    },
    {
        "start": "RelationFact:fact-7a274e626c596c992df5",
        "type": "USES_RELATION",
        "end": "RelationType:forms_primary_material_for",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3026d76c11729aa75d75",
        "type": "USES_RELATION",
        "end": "RelationType:is_recommended_for_storing",
        "props": {},
    },
    {
        "start": "RelationFact:fact-3831b81b601d1e3d4b9b",
        "type": "USES_RELATION",
        "end": "RelationType:require",
        "props": {},
    },
    {
        "start": "RelationFact:fact-50d5618b306780063992",
        "type": "USES_RELATION",
        "end": "RelationType:exhibits_aesthetic",
        "props": {},
    },
    {
        "start": "RelationFact:fact-d7e611f93698ff7506ae",
        "type": "USES_RELATION",
        "end": "RelationType:encourages_reuse_for",
        "props": {},
    },
]

_SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_name(value: str, *, kind: str) -> str:
    name = str(value or "").strip()
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(f"Unsafe Neo4j {kind} name: {value!r}")
    return name


def _node_match(ref: str) -> tuple[str, str, Any]:
    label, raw_value = str(ref).split(":", 1)
    key = UNIQUE_KEYS[label]
    return label, key, _coerce_ref_value(raw_value)


def _coerce_ref_value(value: str) -> Any:
    try:
        return int(value)
    except ValueError:
        return value


def seed_snapshot(driver: Any) -> dict[str, int]:
    with driver.session() as session:
        for node in GRAPH_NODES:
            labels = [_safe_name(label, kind="label") for label in node["labels"]]
            primary_label = labels[0]
            key = UNIQUE_KEYS[primary_label]
            props = dict(node["props"])
            session.run(
                f"MERGE (node:`{primary_label}` {{`{key}`: $key_value}}) SET node += $props",
                key_value=props[key],
                props=props,
            )

        for relationship in GRAPH_RELATIONSHIPS:
            start_label, start_key, start_value = _node_match(relationship["start"])
            end_label, end_key, end_value = _node_match(relationship["end"])
            rel_type = _safe_name(relationship["type"], kind="relationship")
            session.run(
                f"""
                MATCH (start:`{start_label}` {{`{start_key}`: $start_value}})
                MATCH (end:`{end_label}` {{`{end_key}`: $end_value}})
                MERGE (start)-[rel:`{rel_type}`]->(end)
                SET rel += $props
                """,
                start_value=start_value,
                end_value=end_value,
                props=dict(relationship.get("props") or {}),
            )

    return {"nodes": len(GRAPH_NODES), "relationships": len(GRAPH_RELATIONSHIPS)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the temporary forum graph snapshot into Neo4j."
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Delete current Neo4j nodes/relationships before applying this snapshot.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    uri, username, password = read_neo4j_env()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        if args.clear_first:
            deleted_count = clear_graph(driver)
            print(f"Cleared {deleted_count} existing Neo4j nodes.")
        schema_count = apply_schema(driver)
        counts = seed_snapshot(driver)
    finally:
        driver.close()

    print(f"Applied {schema_count} schema statements.")
    print(f"Seeded {counts['nodes']} snapshot nodes.")
    print(f"Seeded {counts['relationships']} snapshot relationships.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
