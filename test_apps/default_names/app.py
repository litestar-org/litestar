from litestar import Litestar

from .a import func as get_a
from .b import func as get_b
from .c import C
from .r import r as router

app = Litestar([get_a, get_b, C, router])
