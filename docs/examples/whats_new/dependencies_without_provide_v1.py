from litestar import Litestar
from litestar.di import Provide


async def some_dependency() -> str: ...


app = Litestar(dependencies={"some": Provide(some_dependency)})
