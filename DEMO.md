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