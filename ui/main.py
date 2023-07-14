import asyncio
import uvicorn
import json
from kafka import KafkaConsumer

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import signal

STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond

app = FastAPI()
app.mount("/static", StaticFiles(directory="static",html = True), name="static")

def stop_kafka_consumer():
    print("Stopping Kafka consumer")
    if consumer:
        consumer.close()

@app.on_event("startup")
async def startup_event():
    global consumer

    consumer = KafkaConsumer(
        bootstrap_servers=["localhost:9092"],
        group_id="demo-group95",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=1000,
        value_deserializer=lambda x: x.decode("utf-8") 
    )
    consumer.subscribe("notifications")
    signal.signal(signal.SIGINT, stop_kafka_consumer)
    signal.signal(signal.SIGTERM, stop_kafka_consumer)

@app.get("/notifications")
async def notifications(request: Request):
    global consumer
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            for message in consumer:
                message_info = f"{message.value}\n\n"
                print(f"{message_info}")

                yield message_info 

            await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())


  
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, access_log=True)
