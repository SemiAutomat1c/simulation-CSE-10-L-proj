# **Basic Version**

!pip install simpy

import simpy

env = simpy.Environment()

def customer(env):
    yield env.timeout(30)
    print(f'Details entered at time: {env.now}')
    yield env.timeout(60)
    print(f'Cash retrieved at time: {env.now}')

env.process(customer(env=env))
env.run()

# **multiple customers**

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

# **Yield removed**

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

# **Code 1a/1b — ATM as a Resource with Queuing**

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

# **Constant Arrival Time**

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

# **Simulation: 1 ATM, 10-minute window**

# ── Install SimPy ─────────────────────────────────────────────────────────────
!pip install simpy -q

import simpy
import random

# ── Step 1: Global Metrics ────────────────────────────────────────────────────
waiting_times = []
cycle_times = []
completed_customers = 0

def customer(env, name, atm):
    global completed_customers

    arrival_time = env.now
    print(f'{name}: Arrives at time {arrival_time:.2f}')

    with atm.request() as request:
        yield request

        start_service = env.now
        waiting_time = start_service - arrival_time
        waiting_times.append(waiting_time)

        print(f'{name}: Starts using ATM at time {start_service:.2f}')
        print(f'{name}: Waiting time = {waiting_time:.2f} seconds')

        # Transaction steps
        yield env.timeout(30)
        yield env.timeout(60)

        end_time = env.now
        cycle_time = end_time - arrival_time
        cycle_times.append(cycle_time)

        completed_customers += 1

        print(f'{name}: Leaves ATM at time {end_time:.2f}')
        print(f'{name}: Cycle time = {cycle_time:.2f} seconds\n')

# ── Step 2: Customer Generator ────────────────────────────────────────────────
def customer_generator(env, atm):
    cust_number = 1

    while True:
        inter_arrival = random.uniform(1, 3) * 60
        yield env.timeout(inter_arrival)

        env.process(customer(env, f"Customer {cust_number}", atm))
        cust_number += 1

# ── Step 3: Simulation Setup ──────────────────────────────────────────────────
SIM_TIME = 10 * 60  # 10 minutes

env = simpy.Environment()
atm = simpy.Resource(env, capacity=1)

env.process(customer_generator(env, atm))
env.run(until=SIM_TIME)

# ── Step 4: Performance Metrics ───────────────────────────────────────────────
if completed_customers > 0:
    avg_waiting_time = sum(waiting_times) / len(waiting_times)
    avg_cycle_time   = sum(cycle_times)   / len(cycle_times)
    throughput_rate  = completed_customers / SIM_TIME  # customers per second

    print("===== PERFORMANCE METRICS =====")
    print(f"Total customers served: {completed_customers}")
    print(f"Average waiting time:   {avg_waiting_time:.2f} seconds")
    print(f"Average cycle time:     {avg_cycle_time:.2f} seconds")
    print(f"Throughput rate:        {throughput_rate:.4f} customers/second")

import simpy
import random

# ── Simulation Function ───────────────────────────────────────────────────────
def run_simulation(num_atms, inter_arrival_min, inter_arrival_max, sim_time, seed=42):
    random.seed(seed)

    waiting_times = []
    cycle_times = []
    completed_customers = [0]

    def customer(env, name, atm):
        arrival_time = env.now

        with atm.request() as request:
            yield request

            start_service = env.now
            waiting_times.append(start_service - arrival_time)

            yield env.timeout(30)
            yield env.timeout(60)

            end_time = env.now
            cycle_times.append(end_time - arrival_time)
            completed_customers[0] += 1

    def customer_generator(env, atm):
        cust_number = 1
        while True:
            inter_arrival = random.uniform(inter_arrival_min, inter_arrival_max) * 60
            yield env.timeout(inter_arrival)
            env.process(customer(env, f"Customer {cust_number}", atm))
            cust_number += 1

    env = simpy.Environment()
    atm = simpy.Resource(env, capacity=num_atms)
    env.process(customer_generator(env, atm))
    env.run(until=sim_time)

    served = completed_customers[0]
    avg_wait  = sum(waiting_times) / len(waiting_times) if waiting_times else 0
    avg_cycle = sum(cycle_times)   / len(cycle_times)   if cycle_times   else 0
    throughput = served / sim_time

    return served, avg_wait, avg_cycle, throughput

# ── Settings ──────────────────────────────────────────────────────────────────
SIM_TIME   = 60 * 60       # 1 hour
NORMAL_MIN, NORMAL_MAX = 1, 3   # normal season: 1–3 min between arrivals
PEAK_MIN,   PEAK_MAX   = 0.3, 1 # peak season:   0.3–1 min (much faster arrivals)

# ── Q1: How many ATMs should we invest? (Normal Season) ──────────────────────
print("=" * 60)
print("Q1: HOW MANY ATMs? (Normal Season)")
print("=" * 60)
print(f"{'ATMs':<6} {'Served':<8} {'Avg Wait (s)':<15} {'Avg Cycle (s)':<15} {'Throughput'}")
print("-" * 60)
for n in range(1, 6):
    served, wait, cycle, tp = run_simulation(n, NORMAL_MIN, NORMAL_MAX, SIM_TIME)
    flag = " ✅ sweet spot" if wait < 30 and n <= 3 else ""
    print(f"{n:<6} {served:<8} {wait:<15.2f} {cycle:<15.2f} {tp:.4f}/s{flag}")

# ── Q2: Are we prepared for peak season? ─────────────────────────────────────
print("\n" + "=" * 60)
print("Q2: PEAK SEASON READINESS (Higher Arrival Rate)")
print("=" * 60)
print(f"{'ATMs':<6} {'Served':<8} {'Avg Wait (s)':<15} {'Avg Cycle (s)':<15} {'Throughput'}")
print("-" * 60)
for n in range(1, 6):
    served, wait, cycle, tp = run_simulation(n, PEAK_MIN, PEAK_MAX, SIM_TIME)
    flag = " ✅ ready" if wait < 60 else " ❌ overloaded"
    print(f"{n:<6} {served:<8} {wait:<15.2f} {cycle:<15.2f} {tp:.4f}/s{flag}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RECOMMENDATION SUMMARY")
print("=" * 60)
print("Normal Season → simulate to find where avg wait drops below 30s")
print("Peak Season   → simulate to find where avg wait stays under 60s")
print("Invest in the minimum number of ATMs that meets both thresholds.")