import quixstreams as qx
from quixstreams import StreamConsumer, EventData
import time
import json
from pinotdb import connect
import pandas as pd
import datetime as dt

conn = connect(host='localhost', port=8099, path='/query/sql', scheme='http')
client = qx.KafkaStreamingClient('127.0.0.1:9092')

topic_consumer = client.get_topic_consumer(
    topic="flight-statuses",
    auto_offset_reset=qx.AutoOffsetReset.Earliest,
    consumer_group="flight-delay-notifications"
)
topic_producer = client.get_raw_topic_producer("massaged-delays")

# topic_producer = client.get_topic_producer(topic = "massaged-delays")
# delays_stream = topic_producer.create_stream()

find_customers_query="""
select arrival_airport, 
       ToDateTime(scheduled_departure_time, 'YYYY-MM-dd HH:mm') AS departure_time, 
       customer_actions.flight_id, 
       passenger_id, Name AS passenger, 
       ToDateTime(ts, 'YYYY-MM-dd HH:mm') AS lastStatusTimestamp, 
       customer_actions.message_type AS lastStatus, 
       customers.Email,
       customers.FrequentFlyerStatus,
       customers.LoyaltyScore,
       customers.NumberOfFlights,
       customers.PastDelays
from customer_actions 
JOIN flight_statuses ON flight_statuses."flight_id" = customer_actions."flight_id"
JOIN customers ON customers.CustomerId = customer_actions.passenger_id
WHERE flight_statuses.flight_id = (%(flightId)s)
ORDER BY ts
LIMIT 500
"""

def on_event_data_received_handler(stream: StreamConsumer, data: EventData):
    with data:
        payload = json.loads(data.value)        
        if payload["message_type"] == "flight_delay":
            print(payload)
            flight_id = payload["data"]["flight_id"]

            epoch_timestamp_sec = payload["data"]["new_departure_time"] / 1000.0
            date = dt.datetime.fromtimestamp(epoch_timestamp_sec)
            new_departure_time = date.strftime("%Y-%m-%d %H:%M")


            curs = conn.cursor()
            curs.execute(find_customers_query, {"flightId": flight_id}, queryOptions="useMultistageEngine=true")
            customers = pd.DataFrame(curs, columns=[item[0] for item in curs.description])
            curs.close()
            for index, customer in customers.iterrows():
                customer_message = customer.to_dict()
                customer_message["new_departure_time"] = new_departure_time

                message = qx.RawMessage(json.dumps(customer_message, indent=2).encode('utf-8'))
                message.key = customer_message["passenger_id"].encode('utf-8')
                topic_producer.publish(message)

def on_stream_received_handler(stream_received: StreamConsumer):
    stream_received.events.on_data_received = on_event_data_received_handler


print("Listening to streams. Press CTRL-C to exit.")

topic_consumer.on_stream_received = on_stream_received_handler
topic_consumer.subscribe()

qx.App.run()
