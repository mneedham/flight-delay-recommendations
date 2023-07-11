# Demo

```bash
docker compose -f docker-compose-m1.yml up
```

Set up Python environment:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Create Redpanda topic:

```bash
rpk topic create \
  -c cleanup.policy=compact \
  -r 1 -p 5 \
  flight-statuses customer-actions
```

Run data generator:

```bash
python datagen.py
```

Check data in Redpanda

Go to http://localhost:8080 or query from the command line:

```bash
rpk topic consume flight-statuses --brokers localhost:9092 | 
jq -Cc '.value | fromjson' | 
head -n5
```

```bash
rpk topic consume customer-actions --brokers localhost:9092 | 
jq -Cc '.value | fromjson' | 
head -n5

Create Pinot table:

```bash
pygmentize -O style=github-dark config/flights/schema.json | less
pygmentize -O style=github-dark config/flights/table.json | less
```

```bash
docker run \
  -v $PWD/config:/config \
  --network flights \
  apachepinot/pinot:0.12.0-arm64 \
  AddTable \
  -schemaFile /config/flights/schema.json \
  -tableConfigFile /config/flights/table.json \
  -controllerHost pinot-controller-flights \
  -exec
```

Go to http://localhost:9000

Querying flight statuses:

```sql
select arrival_airport, count(*)
from flight_statuses 
group by arrival_airport
order by count(*) DESC
limit 10
```

Customer actions:

```bash
pygmentize -O style=github-dark config/customer-actions/schema.json | less
pygmentize -O style=github-dark config/customer-actions/table.json | less
```

```bash
docker run \
  -v $PWD/config:/config \
  --network flights \
  apachepinot/pinot:0.12.0-arm64 \
  AddTable \
  -schemaFile /config/customer-actions/schema.json \
  -tableConfigFile /config/customer-actions/table.json \
  -controllerHost pinot-controller-flights \
  -exec
```

Customers:

```bash
pygmentize -O style=github-dark config/customers/schema.json | less
pygmentize -O style=github-dark config/customers/table.json | less
```

```bash
docker run \
  -v $PWD/config:/config \
  --network flights \
  apachepinot/pinot:0.12.0-arm64 \
  AddTable \
  -schemaFile /config/customers/schema.json \
  -tableConfigFile /config/customers/table.json \
  -controllerHost pinot-controller-flights \
  -exec
```

```sql
SET taskName = 'events-task7';
SET input.fs.className = 'org.apache.pinot.spi.filesystem.LocalPinotFS';
SET includeFileNamePattern='glob:**/*customers.csv';
INSERT INTO customers
FROM FILE 'file:///input/';
```

Who's checked in?

```sql
select * 
from customer_actions 
where message_type = 'check_in'
limit 10
```

Statuses for a booking reference

```sql
select * 
from customer_actions 
where booking_reference = '<booking-ref>'
limit 10
option(skipUpsert=true)
```

How many people have checkedin for a flight?

```sql
select message_type, count(*) 
from customer_actions
where flight_id = '<flightId>'
group by message_type
limit 10
```

## Trigger Delay

First find a popular location:

```sql
select arrival_airport, count(*)
from flight_statuses
group by arrival_airport
order by count(*) DESC
limit 10;
```

Find flights to that destination:

```sql
select flight_id, scheduled_departure_time, airline
from flight_statuses 
where arrival_airport = '<arrival-airport>'
order by scheduled_departure_time
limit 10;
```

```bash
python trigger_delay.py --flight-id <flight-id> --delay-time <delay>
```

Services:

* Delays - Consumes `flight-statuses` and publishes delayed customer details to `massaged-delays`
* Personaliser - Consumes `massaged-delays`, creates peronalised messages, and publishes those to `notifications`
* Dispatcher - Consumes `notifications` and prints those messages to stdout

```bash
python services/delays.py
```

View messages - http://localhost:8080/topics/massaged-delays?p=-1&s=50&o=-1#messages

```bash
python services/personaliser.py
```