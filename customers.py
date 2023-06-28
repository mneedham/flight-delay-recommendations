from faker import Faker
import random
import csv
import uuid

fake = Faker('en_GB')  # For generating UK based data

class Customer:
    def __init__(self, id, full_name, age, gender, location, email, frequent_flyer_status, passport_number, num_flights, loyalty_score, past_delays):
        self.id = id
        self.full_name = full_name
        self.age = age
        self.gender = gender
        self.location = location
        self.email = email
        self.frequent_flyer_status = frequent_flyer_status
        self.passport_number = passport_number
        self.num_flights = num_flights
        self.loyalty_score = loyalty_score
        self.past_delays = past_delays

def create_fake_customer():
    customer_id = str(uuid.uuid4())
    full_name = fake.name()
    age = random.randint(18, 70)
    gender = random.choice(['Male', 'Female'])
    location = fake.city()
    email = fake.email()
    frequent_flyer_status = random.choice(['Bronze', 'Silver', 'Gold', 'Platinum'])
    passport_number = fake.bothify(text='#########')  # Creates a random 9 digit number
    num_flights = random.randint(0, 100)
    loyalty_score = round(random.uniform(1, 5), 2)  # Generates a loyalty score between 1 and 5
    past_delays = random.randint(0, int(num_flights/2))  # Number of past delays should not exceed number of flights taken

    return Customer(customer_id, full_name, age, gender, location, email, frequent_flyer_status, passport_number, num_flights, loyalty_score, past_delays)


def generate_fake_customers(n):
    return [create_fake_customer() for _ in range(n)]


if __name__ == "__main__":
    customers = generate_fake_customers(100000)  # Generate 100 fake customers

    with open('data/customers.csv', 'w') as customers_file:
        writer = csv.writer(customers_file, delimiter=",")
        writer.writerow(["CustomerId", "Name", "Age", "Gender", "Location", "Email", "Frequent Flyer Status", "Passport Number", "Number of Flights", "Loyalty Score", "Past Delays"])
        for customer in customers:
            writer.writerow([
                customer.id,
                customer.full_name, customer.age, customer.gender, customer.location, customer.email, customer.frequent_flyer_status, customer.passport_number, 
                customer.num_flights, customer.loyalty_score, 
                customer.past_delays
            ])
