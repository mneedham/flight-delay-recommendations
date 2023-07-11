import quixstreams as qx
from quixstreams import StreamConsumer, EventData, CancellationTokenSource
import time
import json
from langchain.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from llama_index.bridge.langchain import Document as LCDocument
import sys
import threading

# LLM setup
question="""
{context}
The customer's flight has been delayed.
The next available flight and compensation rules are described above.

Please generate a message for the passenger detailing these options and advising on the best course of action. 
The message doesn't need to be super serious, but be apologetic because they are going to be annoyed.  
Also indicate if they will receive any compensation and say the exact £ amount they will receive.
Take customer details into account when replying and remember that Platinum status is best, then Gold, Silver, Bronze.
Keep the message to say 1 or 2 paragraphs and don't list every option.
Suggest which one you think is best and only use the data provided, don't make stuff up.
"""
prompt = PromptTemplate(
    template=question, input_variables=["context"]
)

client = qx.KafkaStreamingClient('127.0.0.1:9092')

topic_consumer = client.get_topic_consumer(
    topic="massaged-delays",
    auto_offset_reset=qx.AutoOffsetReset.Earliest,
    # consumer_group="massaged-delays-consumer3"
)

events_to_consume = 5
events_consumed = 0
cts = CancellationTokenSource()  # used for interrupting the App


def on_event_data_received_handler(stream: StreamConsumer, data: EventData):
    global events_to_consume, events_consumed, cts
    with data, (producer := client.get_raw_topic_producer("notifications")):
        if events_consumed >= events_to_consume-1:
            threading.Thread(target=lambda: cts.cancel()).start()
            print("should cancel here...")
            cts.cancel()

        events_consumed += 1
        payload = json.loads(data.value)
        print(payload)
        
        flight_id = payload["flight_id"]
        destination = payload["arrival_airport"]
        departure_time = payload["departure_time"]

        documents = [
            LCDocument(page_content=f"""Delayed flight:
            Flight Number: {flight_id}, Destination: {destination} 
            Initial flight time: {departure_time}
            New flight time: 2023-06-28 08:55:07.764000"""),
            LCDocument(page_content="""Compensation rules: 
            Compensation between £200 and £500 for a 3+ hour delay
            Food/Drink vouchers for a 1+ hour delay
            Hotel if flight is delayed until the next day
            """),
            LCDocument(page_content="Frequent flyer statuses are: Bronze', 'Silver', 'Gold', 'Platinum"),
            LCDocument(page_content=f"""
            Customer Details: 
            Name: {payload["passenger"]}, lastStatus: {payload["lastStatus"]}, FrequentFlyerStatus: {payload["FrequentFlyerStatus"]}, LoyaltyScore: {payload["LoyaltyScore"]} out of 5
            """)
        ]

    
        print("".join([doc.page_content for doc in documents]))

        # generate notification 
        # llm = OpenAI(temperature=0)
        # qa_chain = load_qa_chain(llm)
        # answer = qa_chain.run(input_documents=documents, question=question)

        answer = f"Here goes the custom message that will be sent to {payload['passenger']}"

        notification = {
            "message": answer,
            "passenger_id": payload["passenger_id"]
        }

        message = qx.RawMessage(json.dumps(notification, indent=2).encode('utf-8'))
        message.key = payload["passenger_id"].encode('utf-8')
        producer.publish(message)
        
        # take messages
        # pass the context to LLM
        # generate personalised notification for each customer  (3-5 seconds per customer)
        # Publish the message to dispatches

def on_stream_received_handler(stream_received: StreamConsumer):
    stream_received.events.on_data_received = on_event_data_received_handler


print("Listening to streams. Press CTRL-C to exit.")

topic_consumer.on_stream_received = on_stream_received_handler
topic_consumer.subscribe()

def before_shutdown():
    print('before shutdown')

qx.App.run(cts.token, before_shutdown=before_shutdown)
