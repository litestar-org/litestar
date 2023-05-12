from litestar import Litestar
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend

channels_plugin = ChannelsPlugin(
    backend=MemoryChannelsBackend(),
    channels=["foo", "bar"],
    create_ws_route_handlers=True,
)

app = Litestar(plugins=[channels_plugin])
