from litestar import Litestar
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend

channels_plugin = ChannelsPlugin(
    backend=MemoryChannelsBackend(history=10),  # this number should be greater than
    # or equal to the history to be sent
    channels=["foo", "bar"],
    create_ws_route_handlers=True,
    ws_handler_send_history=10,
)

app = Litestar(plugins=[channels_plugin])
