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

Create Pinot table:

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
where booking_reference = 'JU8893-39d38b7a-c7b3-4087-90de-aaac647a3fb7'
limit 10
option(skipUpsert=true)
```

How many people have checkedin for a flight?

```sql
select message_type, count(*) 
from customer_actions
where flight_id = 'JU8893'
group by message_type
limit 10
```