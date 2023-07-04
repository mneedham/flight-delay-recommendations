import quixstreams as qx
from quixstreams import StreamConsumer, EventData
import time
import json

client = qx.KafkaStreamingClient('127.0.0.1:9092')

topic_consumer = client.get_topic_consumer(
    topic="notification",
    auto_offset_reset=qx.AutoOffsetReset.Earliest,
    # consumer_group="flight-delay-notifications"
)


def on_event_data_received_handler(stream: StreamConsumer, data: EventData):
    with data:
        payload = json.loads(data.value)
        
        # generate personalised notification for each customer  (3-5 seconds per customer)

        
        # send out the notifications                            (asynchronous)

def on_stream_received_handler(stream_received: StreamConsumer):
    stream_received.events.on_data_received = on_event_data_received_handler


print("Listening to streams. Press CTRL-C to exit.")

topic_consumer.on_stream_received = on_stream_received_handler
topic_consumer.subscribe()

qx.App.run()