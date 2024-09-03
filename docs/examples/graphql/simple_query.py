from typing import List

import strawberry
from strawberry.litestar import make_graphql_controller

from litestar import Litestar


@strawberry.type
class Movie:
    title: str
    director: str


# This is where you put all your graphql endpoints together
@strawberry.type
class Query:
    @strawberry.field
    # Graqhql endpoint
    def movies(self) -> List[Movie]:
        return [
            Movie(title="The Silent Storm", director="Ella Parker"),
            Movie(title="Whispers in the Wind", director="Daniel Brooks"),
            Movie(title="Echoes of Tomorrow", director="Sophia Rivera"),
            Movie(title="Fading Horizons", director="Lucas Mendes"),
            Movie(title="Broken Dreams", director="Amara Patel"),
        ]


schema = strawberry.Schema(Query)

# Create a controller for the endopint
GraphQLController = make_graphql_controller(
    schema,
    path="/graphql/movies",
)

app = Litestar(route_handlers=[GraphQLController])
