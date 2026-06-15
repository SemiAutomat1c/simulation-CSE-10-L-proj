Run the code in Google Colaboratory. See attached image.
Code # 1
•Model an ATM where a customer arrives. He spends 30
seconds to enter his details (such as PIN and amount) and
it takes another 60 seconds to get the cash.


Code # 2
•Model
an ATM where multiple customers arrive. Each one of them spends 30 seconds to
enter his details (such as PIN and amount) and it takes another 60 seconds to
get the cash.


Basic Version

[ ]
import simpy

env = simpy.Environment()

def customer(env):
    yield env.timeout(30)
    print(f'Details entered at time: {env.now}')
    yield env.timeout(60)
    print(f'Cash retrieved at time: {env.now}')

env.process(customer(env=env))
env.run()
Details entered at time: 30
Cash retrieved at time: 90
multiple customers

[ ]
import simpy
import random

def customer(env, name):
    print(f'{name}: Arrives at time {env.now:.2f}')
    yield env.timeout(30)
    print(f'{name}: Details entered at time: {env.now:.2f}')
    yield env.timeout(60)
    print(f'{name}: Cash retrieved at time: {env.now:.2f}')

def customer_generator(env):
    cust_number = 1
    while True:
        random_inter_arrival_time = random.uniform(1, 3) * 60
        yield env.timeout(random_inter_arrival_time)
        env.process(customer(env=env, name=f"customer {cust_number}"))
        cust_number += 1

env = simpy.Environment()
env.process(customer_generator(env=env))
env.run(until=10*60)  # 10 minutes
customer 1: Arrives at time 124.18
customer 1: Details entered at time: 154.18
customer 1: Cash retrieved at time: 214.18
customer 2: Arrives at time 228.69
customer 2: Details entered at time: 258.69
customer 2: Cash retrieved at time: 318.69
customer 3: Arrives at time 330.40
customer 3: Details entered at time: 360.40
customer 3: Cash retrieved at time: 420.40
customer 4: Arrives at time 488.36
customer 4: Details entered at time: 518.36
customer 4: Cash retrieved at time: 578.36
Yield removed

[ ]
customer 1: Arrives at time 63.27
customer 1: Details entered at time: 63.27
customer 1: Cash retrieved at time: 63.27
customer 2: Arrives at time 188.90
customer 2: Details entered at time: 188.90
customer 2: Cash retrieved at time: 188.90
customer 3: Arrives at time 306.56
customer 3: Details entered at time: 306.56
customer 3: Cash retrieved at time: 306.56
customer 4: Arrives at time 444.63
customer 4: Details entered at time: 444.63
customer 4: Cash retrieved at time: 444.63
customer 5: Arrives at time 511.31
customer 5: Details entered at time: 511.31
customer 5: Cash retrieved at time: 511.31
