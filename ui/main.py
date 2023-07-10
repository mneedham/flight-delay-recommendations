import asyncio
import uvicorn
import json
from kafka import KafkaConsumer

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond

app = FastAPI()
app.mount("/static", StaticFiles(directory="static",html = True), name="static")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/notifications")
async def notifications(request: Request):
    consumer = KafkaConsumer(
        bootstrap_servers=["localhost:9092"],
        group_id="demo-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=1000
    )

    consumer.subscribe("notifications")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            for message in consumer:
                message_info = f"key: {message.key}, {message.value}"
                print(f"{message_info}")

                yield message_info 

        await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())



  



