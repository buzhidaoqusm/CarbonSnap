"""CarbonSnap backend.

Importing the package registers every model on Base.metadata, so a mapper
that names another model by string can always resolve it.
"""

import app.models  # noqa: F401
