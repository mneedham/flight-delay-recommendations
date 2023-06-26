# Flight Delay Recommendations


## Flight statuses

* Scheduled: This status indicates that the flight is still expected to leave at the originally planned departure time.
* Check-in: The check-in for the flight is open.
* Check-in Closed: The check-in for the flight is closed.
* Boarding: Passengers are currently being boarded onto the flight.
* Final Call: The last announcement for passengers to board.
* Gate Change: The departure gate for the flight has changed (this could technically happen at any time before departure).
* On Time: The flight is expected to depart or arrive at the originally scheduled time.
* Delayed: The flight’s departure or arrival has been postponed (this could happen before or after the "On Time" status, depending on circumstances).
* Departed: The flight has left the departure airport.
* In Flight: The flight is currently in the air.
* Diverted: The flight has been diverted to a different airport due to some kind of issue (e.g., weather conditions, mechanical problems, etc.).
* Landed: The flight has landed at the destination airport.
* Baggage Claim: Luggage from the flight is now available for pickup.
* Note: The Cancelled status could technically occur at any time, from just after the flight is scheduled to just before it's supposed to depart.

## Data

Data that we could use:

### About the person

flight details (OLTP)
return flight (OLTP)
previous flights
business/personal
is anybody travelling with you e.g. any children?
loyalty points
are you travelling inbound or outbound

### Other

Alternative flights
Alternative other transport
Hotel availability
Airline policy on flight delays

## The app

### v1
* Stream of events
* Streamlit UI where we can trigger delayed events. (how long and which flight). Also want to be able to see notifications for multiple users
* Filter the delayed events with quix/rising wave. Create a prompt and call OpenAI. Get back a message. “Send” to the user via a pub/sub or RP topic? If all else fails, log the notification to the console!


### v2
* Add in the company’s delay policy
* Users previous flight history
* Whether the booking was personal/business
* Are they going inbound/outbound
* Can we offer any vouchers?
* https://novu.co/

## Why LLM?

Why would you use an LLM instead of <other-tool>:

* More flexible
* Faster maintenance - literally adjust the prompt with new data
* Personalised suggestions

Things to keep in our head:

* Is the LLM doing something that we couldn’t do with a well designed UI?
* The things that it can do: make suggestions and curate a lot of data in a clean way
