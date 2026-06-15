Basic Version

[ ]
!pip install simpy
Collecting simpy
  Downloading simpy-4.1.1-py3-none-any.whl.metadata (6.1 kB)
Downloading simpy-4.1.1-py3-none-any.whl (27 kB)
Installing collected packages: simpy
Successfully installed simpy-4.1.1

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
customer 1: Arrives at time 120.23
customer 1: Details entered at time: 150.23
customer 1: Cash retrieved at time: 210.23
customer 2: Arrives at time 246.35
customer 2: Details entered at time: 276.35
customer 2: Cash retrieved at time: 336.35
customer 3: Arrives at time 338.16
customer 3: Details entered at time: 368.16
customer 3: Cash retrieved at time: 428.16
customer 4: Arrives at time 479.06
customer 4: Details entered at time: 509.06
customer 5: Arrives at time 544.33
customer 4: Cash retrieved at time: 569.06
customer 5: Details entered at time: 574.33
Yield removed

[ ]
import simpy
import random

def customer(env, name):
    print(f'{name}: Arrives at time {env.now:.2f}')
    # yield env.timeout(30)  ← REMOVED
    print(f'{name}: Details entered at time: {env.now:.2f}')
    # yield env.timeout(60)  ← REMOVED
    print(f'{name}: Cash retrieved at time: {env.now:.2f}')
    yield env.timeout(0)  # ← dummy yield t

def customer_generator(env):
    cust_number = 1
    while True:
        random_inter_arrival_time = random.uniform(1, 3) * 60
        yield env.timeout(random_inter_arrival_time)
        env.process(customer(env=env, name=f"customer {cust_number}"))
        cust_number += 1

env = simpy.Environment()
env.process(customer_generator(env=env))
env.run(until=10*60)
customer 1: Arrives at time 116.99
customer 1: Details entered at time: 116.99
customer 1: Cash retrieved at time: 116.99
customer 2: Arrives at time 244.89
customer 2: Details entered at time: 244.89
customer 2: Cash retrieved at time: 244.89
customer 3: Arrives at time 320.56
customer 3: Details entered at time: 320.56
customer 3: Cash retrieved at time: 320.56
customer 4: Arrives at time 434.33
customer 4: Details entered at time: 434.33
customer 4: Cash retrieved at time: 434.33
customer 5: Arrives at time 494.69
customer 5: Details entered at time: 494.69
customer 5: Cash retrieved at time: 494.69
Code 1a/1b — ATM as a Resource with Queuing

[ ]
import simpy
import random

def customer(env, name, atm):
    print(f'{name}: Arrives at time {env.now:.2f}')

    with atm.request() as request:
        yield request  # wait until ATM is available
        print(f'{name}: Starts using ATM at time {env.now:.2f}')

        yield env.timeout(30)
        print(f'{name}: Details entered at time: {env.now:.2f}')

        yield env.timeout(60)
        print(f'{name}: Cash retrieved at time: {env.now:.2f}')

        print(f'{name}: Leaves ATM at time {env.now:.2f}')

def customer_generator(env, atm):
    cust_number = 1
    while True:
        inter_arrival = random.uniform(1, 3) * 60
        yield env.timeout(inter_arrival)
        env.process(customer(env, f"customer {cust_number}", atm))
        cust_number += 1

random.seed(2)
env = simpy.Environment()
atm = simpy.Resource(env, capacity=1)  # only 1 customer at a time

env.process(customer_generator(env, atm))
env.run(until=10 * 60)
customer 1: Arrives at time 174.72
customer 1: Starts using ATM at time 174.72
customer 1: Details entered at time: 204.72
customer 1: Cash retrieved at time: 264.72
customer 1: Leaves ATM at time 264.72
customer 2: Arrives at time 348.46
customer 2: Starts using ATM at time 348.46
customer 2: Details entered at time: 378.46
customer 3: Arrives at time 415.25
customer 2: Cash retrieved at time: 438.46
customer 2: Leaves ATM at time 438.46
customer 3: Starts using ATM at time 438.46
customer 3: Details entered at time: 468.46
customer 4: Arrives at time 485.43
customer 3: Cash retrieved at time: 528.46
customer 3: Leaves ATM at time 528.46
customer 4: Starts using ATM at time 528.46
customer 4: Details entered at time: 558.46
Constant Arrival Time

[ ]
import simpy
import random

def customer(env, name, atm):
    print(f'{name}: Arrives at time {env.now:.2f}')

    with atm.request() as request:
        yield request
        print(f'{name}: Starts using ATM at time {env.now:.2f}')

        yield env.timeout(30)
        print(f'{name}: Details entered at time: {env.now:.2f}')

        yield env.timeout(60)
        print(f'{name}: Cash retrieved at time: {env.now:.2f}')

        print(f'{name}: Leaves ATM at time {env.now:.2f}')

def customer_generator(env, atm):
    cust_number = 1
    while True:
        inter_arrival = 120  # every 2 minutes EXACTLY (constant)
        yield env.timeout(inter_arrival)
        env.process(customer(env, f"customer {cust_number}", atm))
        cust_number += 1

env = simpy.Environment()
atm = simpy.Resource(env, capacity=1)

env.process(customer_generator(env, atm))
env.run(until=10 * 60)
customer 1: Arrives at time 120.00
customer 1: Starts using ATM at time 120.00
customer 1: Details entered at time: 150.00
customer 1: Cash retrieved at time: 210.00
customer 1: Leaves ATM at time 210.00
customer 2: Arrives at time 240.00
customer 2: Starts using ATM at time 240.00
customer 2: Details entered at time: 270.00
customer 2: Cash retrieved at time: 330.00
customer 2: Leaves ATM at time 330.00
customer 3: Arrives at time 360.00
customer 3: Starts using ATM at time 360.00
customer 3: Details entered at time: 390.00
customer 3: Cash retrieved at time: 450.00
customer 3: Leaves ATM at time 450.00
customer 4: Arrives at time 480.00
customer 4: Starts using ATM at time 480.00
customer 4: Details entered at time: 510.00
customer 4: Cash retrieved at time: 570.00
customer 4: Leaves ATM at time 570.00
