from twisted.web import server, resource
from twisted.internet import reactor, task, endpoints, threads, defer
from faker import Faker
from faker_airtravel import AirTravelProvider
import faker_airtravel
from datetime import datetime, timedelta
import random
from random import choice, randint, sample
import json
import csv

from confluent_kafka import Producer

fake = Faker()
fake.add_provider(AirTravelProvider)

with open('data/destinations.csv', 'r') as destinations_file:
    reader = csv.DictReader(destinations_file)
    destinations = {row['AirportCode']: {**row, "Airlines": [fake.airline() for _ in range(2 if int(row["Weight"]) < 7 else 3)]} for row in reader}


plane_seats = {
    'Boeing 737': 188,
    'Airbus A320': 180,
    'Boeing 747': 416,
    'Boeing 777': 365,
    'Airbus A330': 335,
    'Airbus A380': 544,
    'Boeing 767': 218,
    'Boeing 757': 200,
    'Airbus A350': 315,
    'Boeing 787': 242,
    'Bombardier CRJ700': 70,
    'Embraer E175': 76,
    'Bombardier Q400': 78,
    'Airbus A319': 124,
    'Airbus A380plus': 600
}

flights = {}
producer = Producer({'bootstrap.servers': 'localhost:9092'})

def emit_events():
    global flights
    print('emit events')


def ebLoopFailed(failure):
    """
    Called when loop execution failed.
    """
    print("ebLoopFailed")
    print(str(failure))
    # reactor.stop()


def cbLoopDone(result):
    """
    Called when loop was stopped with success.
    """
    print("cbLoopDone")
    print("Race finished.")
    # reactor.stop()

# Function to generate random airline flight number
def random_flight_id(airline, existing_ids):
    flight_id = airline[:2].upper() + str(fake.random_int(min=1000, max=9999))
    while flight_id in existing_ids:
        flight_id = airline[:2].upper() + str(fake.random_int(min=1000, max=9999))
    existing_ids.add(flight_id)
    return flight_id

def random_aircraft_model():
    return choice(list(plane_seats.keys()))

def acked(err, msg):
    if err is not None:
        print("Failed to deliver message: {0}: {1}"
              .format(msg.value(), err.str()))

def json_serializer(obj):
    if isinstance(obj, datetime):  # This refers to datetime.datetime because of your import
        return obj.strftime("%Y-%m-%d %T%Z")
    raise TypeError("Type %s not serializable" % type(obj))

def publish_flight(producer, event):    
    try:
        payload = json.dumps(event, default=json_serializer, ensure_ascii=False).encode('utf-8')
        producer.produce(topic='flight-statuses', key=str(event['data']['flight_id']), value=payload, callback=acked)
    except TypeError:
        print(f"Failed to parse: {event}")

def run_loop():
    # site = server.Site(Courses())
    # endpoint = endpoints.TCP4ServerEndpoint(reactor, 8080)
    # endpoint.listen(site)

    dep_time = datetime.now()
    existing_ids = set()
    for i in range(600):     
        uk_airports = [airport for airport in faker_airtravel.constants.airport_list if airport['iata'] == 'LHR']
        dep_airport = next((airport for airport in faker_airtravel.constants.airport_list if airport['iata'] == 'LHR'), {})

        valid_iatas = [airport['iata'] for airport in faker_airtravel.constants.airport_list]
        weighted_airports = [(iata, int(airport['Weight'])) for iata, airport in destinations.items() if iata in valid_iatas]
        arr_iata, *_ = random.choices([airport for airport, _ in weighted_airports], weights=[weight for _, weight in weighted_airports])
        arr_airport = next((airport for airport in faker_airtravel.constants.airport_list if airport['iata'] == arr_iata), {})

        airline = choice(destinations[arr_iata]["Airlines"])
        
        arr_time = dep_time + timedelta(hours=random.randint(1, 6))
        flight_id = random_flight_id(airline, existing_ids)
        aircraft = random_aircraft_model()
        flights[flight_id] = {
            "message_type": "flight_schedule",
            "data": {
                "flight_id": flight_id,
                "airline": airline,
                "departure_airport": dep_airport,
                "arrival_airport": arr_airport,
                "scheduled_departure_time": int(dep_time.timestamp() * 1000),
                "scheduled_arrival_time": int(arr_time.timestamp() * 1000),
                "aircraft_type": aircraft,
                "available_seats": plane_seats[aircraft]
            }
        }

        dep_time += timedelta(minutes=3)
        
    print(len(flights.items())) 
    for flight_id, flight_details in flights.items():
        # print(flight_details)
        publish_flight(producer, flight_details)

    l = task.LoopingCall(emit_events)
    loop_deferred = l.start(1.0)
    loop_deferred.addErrback(ebLoopFailed)
    loop_deferred.addCallback(cbLoopDone)

    reactor.run()


if __name__ == "__main__":
    run_loop()
