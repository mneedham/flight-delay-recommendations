import quixstreams as qx
from quixstreams import StreamConsumer, EventData, CancellationTokenSource, CommitMode
import time
import json
from langchain.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from llama_index.bridge.langchain import Document as LCDocument
import sys
import threading

from llama_index import download_loader
import datetime as dt

# LLM setup
question="""
{context}
The customer's flight has been delayed.
The details about the flight, as well as next available flights and compensation rules are described above.

Generate a message fo the customer advising on the best course of action. 
Make sure you mention flight number, destination, and departure time.
Please be apologetic because they are going to be annoyed.  
Indicate if they will receive any compensation and don't tell them the range, tell them the exact £ amount they will receive.
Take customer details into account when replying and remember that Platinum status is best, then Gold, Silver, Bronze.
When choosing the next available flight, give the soonest flights to people highest status, but don't mention their status in your reasoning and only suggest one flight.
Keep the message to 1 or 2 paragraphs and don't list every option.
Suggest which one you think is best and only use the data provided, don't make stuff up.
"""
prompt = PromptTemplate(
    template=question, input_variables=["context"]
)

llm = OpenAI(temperature=0,)
qa_chain = load_qa_chain(llm)

client = qx.KafkaStreamingClient('127.0.0.1:9092')

DatabaseReader = download_loader('DatabaseReader')
reader = DatabaseReader(
    uri="pinot+http://localhost:8099/query/sql?controller=http://localhost:9000"
)



topic_consumer = client.get_topic_consumer(
    topic="massaged-delays",
    auto_offset_reset=qx.AutoOffsetReset.Earliest,
    consumer_group="massaged-delays-consumer4",
    commit_settings=CommitMode.Manual
)
producer = client.get_raw_topic_producer("notifications")

events_to_consume = 1
events_consumed = 0
threadLock = threading.Lock()

cts = CancellationTokenSource()
cancellation_thread = threading.Thread(target=lambda: cts.cancel())


def create_context_messages(payload):
        flight_id = payload["flight_id"]
        destination = payload["arrival_airport"]
        departure_time = payload["departure_time"]

        dep_time = dt.datetime.strptime(departure_time, "%Y-%m-%d %H:%M")

        query = f"""
            SELECT 'Next Available Flight' as description, 
            ToDateTime(scheduled_departure_time, 'YYYY-MM-dd HH:mm') AS scheduledDepartureTime, 
            flight_id
            FROM flight_statuses
            WHERE arrival_airport = '{destination}'
            AND scheduled_departure_time > {int(dep_time.timestamp() * 1000)}
            AND flight_id <> '{flight_id}'
            ORDER BY scheduled_departure_time
            LIMIT 5
        """

        documents = reader.load_langchain_documents(query=query)

        return documents + [
            LCDocument(page_content=f"""Delayed flight:
            Flight Number: {flight_id}, Destination: {destination},
            Departure time: {departure_time}"""),
            LCDocument(page_content="""Compensation rules: 
            Compensation between £200 and £500 for a 3+ hour delay
            Food/Drink vouchers for a 1+ hour delay
            Hotel if flight is delayed until the next day
            """),
            LCDocument(page_content="Frequent flyer statuses are: 'Bronze', 'Silver', 'Gold', 'Platinum'"),
            LCDocument(page_content=f"""
            Customer Details: 
            Name: {payload["passenger"]}, lastStatus: {payload["lastStatus"]}, FrequentFlyerStatus: {payload["FrequentFlyerStatus"]}, LoyaltyScore: {payload["LoyaltyScore"]} out of 5
            """)
        ]


def on_event_data_received_handler(stream: StreamConsumer, data: EventData):
    global events_to_consume, events_consumed, cts, topic_consumer
    with data:
        if events_consumed >= events_to_consume:
            if not cancellation_thread.is_alive():
                cancellation_thread.start()
                print("Cancellation token triggered")
            return

        with threadLock:
            events_consumed += 1
        payload = json.loads(data.value)
        print(payload)
        
        documents = create_context_messages(payload)    
        print(f"{events_consumed}: {''.join([doc.page_content for doc in documents])}")

        answer = qa_chain.run(input_documents=documents, question=question)
        print(answer)

        # answer = f"Here goes the super message that will be sent to {payload['passenger']}"
        notification = {
            "message": answer,
            "passenger_id": payload["passenger_id"]
        }

        message = qx.RawMessage(json.dumps(notification, indent=2).encode('utf-8'))
        message.key = payload["passenger_id"].encode('utf-8')
        producer.publish(message)

        topic_consumer.commit()

def on_stream_received_handler(stream_received: StreamConsumer):
    stream_received.events.on_data_received = on_event_data_received_handler


print("Listening to streams. Press CTRL-C to exit.")

topic_consumer.on_stream_received = on_stream_received_handler
topic_consumer.subscribe()

def before_shutdown():
    print('before shutdown')    
    topic_consumer.dispose()
    time.sleep(1)
    producer.dispose()    
    time.sleep(1)

qx.App.run(cts.token, before_shutdown=before_shutdown)
cancellation_thread.join()