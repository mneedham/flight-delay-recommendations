from confluent_kafka import Producer
import json
from datetime import datetime, timedelta
from pinotdb import connect
from llama_index import download_loader
from langchain.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain
from llama_index.bridge.langchain import Document as LCDocument
from langchain.llms import OpenAI

flight_id = "LI1022"

# producer = Producer({'bootstrap.servers': 'localhost:9092'})

# def acked(err, msg):
#     if err is not None:
#         print("Failed to deliver message: {0}: {1}"
#               .format(msg.value(), err.str()))

# def json_serializer(obj):
#     if isinstance(obj, datetime):  # This refers to datetime.datetime because of your import
#         return obj.strftime("%Y-%m-%d %T%Z")
#     raise TypeError("Type %s not serializable" % type(obj))

# def publish_flight(producer, event):    
#     try:
#         payload = json.dumps(event, default=json_serializer, ensure_ascii=False).encode('utf-8')
#         producer.produce(topic='flight-statuses', key=str(event['data']['flight_id']), value=payload, callback=acked)
#     except TypeError:
#         print(f"Failed to parse: {event}")

conn = connect(host='localhost', port=8099, path='/query/sql', scheme='http')

DatabaseReader = download_loader('DatabaseReader')

reader = DatabaseReader(
    uri="pinot+http://localhost:8099/query/sql?controller=http://localhost:9000"
)

flight_details = {
    "data": {
        "flight_id": flight_id
    }
}

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

    query = f"""
        SELECT 'Next Available Flight' as description, scheduled_departure_time, arrival_airport
        FROM flight_statuses
        WHERE arrival_airport = '{destination}'
        AND scheduled_departure_time > {int(departure_time.timestamp() * 1000)}
        AND flight_id <> '{flight_id}'
        ORDER BY scheduled_departure_time
        LIMIT 10
    """

    documents = reader.load_langchain_documents(query=query)
    documents += [LCDocument(page_content=f"Cancelled flight || Flight Number: {flight_id}, Delay Time: 5 hours")]

    llm = OpenAI(temperature=0)

    qa_chain = load_qa_chain(llm)
    question="""
    The attached flight has been cancelled by a number of hours.
    The next available flights are included.
    Please generate a message for the passenger detailing these options and advising on the best course of action. 
    The message doesn't need to be super serious, but be apologetic because they are going to be annoyed.  
    Also indicate if they will receive any compensation
    Keep the message to say 1 or 2 paragraphs and don't list every option. Suggest which one you think is best.
    """
    answer = qa_chain.run(input_documents=documents, question=question)
    print(answer)