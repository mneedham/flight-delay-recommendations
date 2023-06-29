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

with open('data/customers.csv', 'r') as customers_file:
    reader = csv.DictReader(customers_file)
    customers = {row["CustomerId"]: row for row in reader}

conn = connect(host='localhost', port=8099, path='/query/sql', scheme='http')

DatabaseReader = download_loader('DatabaseReader')
reader = DatabaseReader(
    uri="pinot+http://localhost:8099/query/sql?controller=http://localhost:9000"
)

@click.option("--flight_id", help="Flight ID")
def delay_triggered(flight_id):


    random_customer_id = random.choice(list(customers.keys()))
    random_customer = customers[random_customer_id]

    keys_to_remove = ['Location', 'Email', 'Passport Number']
    relevant_customer_data = random_customer = {key: random_customer[key] for key in random_customer if key not in keys_to_remove}

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
            SELECT 'Next Available Flight' as description, scheduled_departure_time
            FROM flight_statuses
            WHERE arrival_airport = '{destination}'
            AND scheduled_departure_time > {int(departure_time.timestamp() * 1000)}
            AND flight_id <> '{flight_id}'
            ORDER BY scheduled_departure_time
            LIMIT 1
        """

        documents = reader.load_langchain_documents(query=query)
        documents += [
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
            LCDocument(page_content=f"Customer details: {', '.join(f'{key}: {value}' for key, value in relevant_customer_data.items())}")
        ]

        for d in documents:
            print(d)

        print(" ".join(d.page_content for d in documents))

        llm = OpenAI(temperature=0)

        qa_chain = load_qa_chain(llm)
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

        answer = qa_chain.run(input_documents=documents, question=question)
        print(answer)

if __name__ == "__main__":
    delay_triggered()
