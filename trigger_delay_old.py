import json
from datetime import datetime, timedelta
from pinotdb import connect
from llama_index import download_loader
from langchain.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain
from llama_index.bridge.langchain import Document as LCDocument
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import csv
import random
import click
import pandas as pd

from confluent_kafka import Producer

conn = connect(host='localhost', port=8099, path='/query/sql', scheme='http')

DatabaseReader = download_loader('DatabaseReader')
reader = DatabaseReader(
    uri="pinot+http://localhost:8099/query/sql?controller=http://localhost:9000"
)

def acked(err, msg):
    if err is not None:
        print("Failed to deliver message: {0}: {1}"
              .format(msg.value(), err.str()))

def json_serializer(obj):
    if isinstance(obj, datetime):  # This refers to datetime.datetime because of your import
        return obj.strftime("%Y-%m-%d %T%Z")
    raise TypeError("Type %s not serializable" % type(obj))

def publish_event(producer, topic, event, key):    
    try:
        payload = json.dumps(event, default=json_serializer, ensure_ascii=False).encode('utf-8')
        producer.produce(topic=topic, key=str(key), value=payload, callback=acked)
    except TypeError:
        print(f"Failed to parse: {event}")


@click.command()
@click.option("--flight-id", help="Flight ID", required=True)
@click.option("--delay-time", default=60, help="Delay in minutes")
def delay_triggered(flight_id, delay_time):
    curs = conn.cursor()
    curs.execute("""
        SELECT scheduled_departure_time, arrival_airport
        FROM flight_statuses
        WHERE flight_id = (%(flightId)s)
        LIMIT 10
    """, {"flightId": flight_id},)
    flight = next(curs, None)

    if flight:
        departure_time, destination = flight
        print(destination, departure_time)
        producer = Producer({'bootstrap.servers': 'localhost:9092'})
        event = {
            "message_type": "flight_delay",
            "data": {
                "flight_id": flight_id,
                "scheduled_departure_time": int(departure_time.timestamp() * 1000),
                "new_departure_time": int(departure_time.timestamp() * 1000) + (delay_time * 60 * 1000)
            }
        }
        print(event)
        publish_event(producer, "flight-statuses", event, key=event["data"]["flight_id"])
        producer.flush()

        query = f"""
            SELECT 'Next Available Flight' as description, scheduled_departure_time
            FROM flight_statuses
            WHERE arrival_airport = '{destination}'
            AND scheduled_departure_time > {int(departure_time.timestamp() * 1000)}
            AND flight_id <> '{flight_id}'
            ORDER BY scheduled_departure_time
            LIMIT 1
        """

        print("flight_id", flight_id)
        curs.execute(f"""
        select arrival_airport, customer_actions.flight_id, passenger_id, Name, ToDateTime(ts, 'YYYY-MM-dd HH:mm') AS ts, customer_actions.message_type AS status
        from customer_actions 
        JOIN flight_statuses ON flight_statuses."flight_id" = customer_actions."flight_id"
        JOIN customers ON customers.CustomerId = customer_actions.passenger_id
        WHERE flight_statuses.flight_id = '{flight_id}'
        ORDER BY ts
        LIMIT 500
        """, {"flightId": flight_id}, queryOptions="useMultistageEngine=true")
        customers = pd.DataFrame(curs, columns=[item[0] for item in curs.description])
        print(customers)

if __name__ == "__main__":
    delay_triggered()
