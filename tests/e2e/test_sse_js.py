import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from playwright.async_api import async_playwright
from uvicorn.config import Config
from uvicorn.server import Server

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData


@get("/test_sse_empty")
async def handler() -> ServerSentEvent:
    async def generate() -> AsyncIterator[SSEData]:
        event = ServerSentEventMessage(event="empty")
        yield event

    return ServerSentEvent(generate())


html = """<!DOCTYPE html>
<html lang="en">
<body>
<h2>Server-Sent Events</h2>
<div id="output"></div>
<script>
    if (typeof EventSource !== "undefined") {
        var eventSource = new EventSource("http://localhost:8765/test_sse_empty");
        eventSource.onmessage = function (event) {
            // console.log(event.data);
            document.getElementById("output").innerHTML += event.data + "<br>";
        };
        eventSource.addEventListener("empty", (ev) => {
            // console.log("empty arrived");
            document.getElementById("output").innerHTML += "endx arrived" + "<br>";
            eventSource.close();
        });

        eventSource.addEventListener("error", (err) => {
            // console.error(err)
            document.getElementById("output").innerHTML += "error: " + err + "<br>";
        })
    } else {
        document.getElementById("output").innerHTML =
            // If browser does not support SSE
            "Sorry, the browser does not support SSE";
    }
</script>
</body>
</html>"""


@asynccontextmanager
async def run_server(config: Config, sockets=None):
    server = Server(config=config)
    task = asyncio.create_task(server.serve(sockets=sockets))
    await asyncio.sleep(0.1)
    try:
        yield server
    finally:
        await server.shutdown()
        task.cancel()


async def test_get_started_link(tmp_path: Path) -> None:
    app = Litestar(route_handlers=[handler], cors_config=CORSConfig(allow_origins=["*"]))
    index = tmp_path / "index.html"
    index.write_text(html)
    async with run_server(config=Config(app=app, port=8765, lifespan="off")):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(f"file://{index.as_posix()}")
            # Click the get started link.#
            output_div_content = await page.query_selector("div#output")
            print(await output_div_content.inner_text())
            await browser.close()
