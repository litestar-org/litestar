from litestar import Litestar
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend

channels_plugin = ChannelsPlugin(
    backend=MemoryChannelsBackend(history=10),  # set the amount of messages per channel
    # to keep in the backend
    channels=["foo", "bar"],
    create_ws_route_handlers=True,
    ws_handler_send_history=10,  # send 10 entries of the history by default
)

app = Litestar(plugins=[channels_plugin])
