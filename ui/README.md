
# The Notifications UI
This module mimics a client applicaiton, typically, a web or mobile app that is owned by a passenger of the airline. The intended purpose of this module is to read personalized recommendations from Redpanda and display them on the UI.

This module consists of:
 - A Server-sent Events (SSE) server based on FastAPI, that consumes messages from the `notifications` Redpanda topic and streams them over the `/notifications` SSE API endpoint.
 - A simple HTML page, `index.html` that consumes the above SSE events and renders them on the UI.

## Setting up

Set up FastAPI dependencies.

```
pip install "fastapi[all]"
pip install sse-starlette
pip install asyncio
```

Run FastAPI server by:

```
uvicorn main:app --reload
```

Visit http://localhost:8000/static to see the UI.

## Produce messages to Redpanda

```
docker exec -ti redpanda rpk topic produce notifications
Hello world
Here goes the second message
```
When messages are produced, you should be able to see them on the UI.
