"""
Food Delivery System — Producer-Consumer Simulation
====================================================
Restaurants (producers) place orders into a shared queue.
Riders (consumers) pick up and deliver those orders.

Part A: Bounded Buffer   — max 5 orders at a time
Part B: Unbounded Buffer — no limit on queue size
"""

import threading
import time
import random
import queue
from collections import defaultdict


# ---------------- COLORS (for better output readability) ----------------
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# ---------------- LOCKS (for thread safety) ----------------
# Prevents mixed/overlapping print output
print_lock = threading.Lock()

# Protects shared statistics dictionary
stats_lock = threading.Lock()

# Protects global order counter
order_counter_lock = threading.Lock()


# ---------------- GLOBAL VARIABLES ----------------
order_counter = 0  # unique ID for each order

# Stores statistics like produced, consumed, waits
stats = defaultdict(int)

# Random food items for simulation
FOOD_ITEMS = ["Biryani", "Pizza", "Burger", "ChowMein", "Dessert",
              "Pasta", "Shawarma", "Ramen", "Kabab", "Chicken Handi"]

# Delays simulate real-world time
PRODUCE_DELAY = 0.2
CONSUME_DELAY = 0.6

# Buffer size for bounded case
BUFFER_CAPACITY = 5


# ---------------- LOG FUNCTION ----------------
# Ensures clean printing using lock
def log(symbol, color, agent, msg):
    with print_lock:
        print(f"  {color}{symbol} {BOLD}{agent:<18}{RESET}{color}{msg}{RESET}")


# ---------------- ORDER ID GENERATOR ----------------
# Generates unique order IDs safely across threads
def next_order_id():
    global order_counter
    with order_counter_lock:
        order_counter += 1
        return order_counter


# ---------------- PRODUCER FUNCTION (Restaurant) ----------------
def restaurant(name, buf, bounded, capacity, produce_count, stop_event):
    produced_local = 0  # count of orders produced by this restaurant

    # Run until required orders are produced OR stop signal
    while produced_local < produce_count and not stop_event.is_set():

        # Create order
        oid  = next_order_id()
        item = random.choice(FOOD_ITEMS)

        order = {"id": oid, "item": item, "restaurant": name}

        # If bounded buffer is full → producer must wait
        if bounded and buf.full():
            log("⏳", YELLOW, name,
                f"Queue FULL ({buf.qsize()}/{capacity}) — restaurant is waiting...")
            with stats_lock:
                stats["producer_waits"] += 1

        # Add order to buffer (shared queue)
        buf.put(order)

        produced_local += 1

        # Update produced count
        with stats_lock:
            stats["produced"] += 1

        # Display queue status
        label = f"{buf.qsize()}/{capacity}" if bounded else str(buf.qsize())

        log("🍳", GREEN, name,
            f"Order #{oid:04d} placed  → {item:<12}  [queue: {label}]")

        # Simulate delay in production
        time.sleep(random.uniform(PRODUCE_DELAY * 0.8, PRODUCE_DELAY * 1.2))

    # When restaurant finishes producing
    log("✅", DIM, name, "Done placing orders.")


# ---------------- CONSUMER FUNCTION (Rider) ----------------
def rider(name, buf, stop_event):

    # Run until stop signal is given
    while not stop_event.is_set():
        try:
            # Try to get order from queue
            order = buf.get(timeout=1.0)

        except queue.Empty:
            # If queue empty → rider waits
            log("💤", YELLOW, name, "Queue EMPTY — rider is waiting for an order...")
            with stats_lock:
                stats["consumer_waits"] += 1
            continue

        # Display picked order
        log("🚴", BLUE, name,
            f"Picked up #{order['id']:04d}  → {order['item']:<12}  "
            f"(from {order['restaurant']})  [queue: {buf.qsize()}]")

        # Simulate delivery time
        time.sleep(random.uniform(CONSUME_DELAY * 0.8, CONSUME_DELAY * 1.2))

        # Update consumed count
        with stats_lock:
            stats["consumed"] += 1

        # Mark task as done in queue
        buf.task_done()


# ---------------- RUN SIMULATION ----------------
def run_simulation(mode, n_producers, n_consumers, orders_per_producer):

    # Check buffer type
    bounded  = (mode == "bounded")

    # Set capacity (0 means unbounded)
    capacity = BUFFER_CAPACITY if bounded else 0

    # Shared queue (buffer)
    buf = queue.Queue(maxsize=capacity)

    # Event used to stop threads
    stop_event = threading.Event()

    # Reset order counter and stats
    global order_counter
    order_counter = 0

    for k in ("produced", "consumed", "producer_waits", "consumer_waits"):
        stats[k] = 0

    # Generate names for restaurants and riders
    r_names = [f"Restaurant-{chr(65+i)}" for i in range(n_producers)]
    a_names = [f"Rider-{i+1}" for i in range(n_consumers)]

    # Create producer threads
    producers = [
        threading.Thread(target=restaurant,
            args=(r_names[i], buf, bounded, BUFFER_CAPACITY,
                  orders_per_producer, stop_event), daemon=True)
        for i in range(n_producers)
    ]

    # Create consumer threads
    consumers = [
        threading.Thread(target=rider,
            args=(a_names[i], buf, stop_event), daemon=True)
        for i in range(n_consumers)
    ]

    # Start all threads
    for t in producers: t.start()
    for t in consumers: t.start()

    # Wait until all producers finish
    for t in producers: t.join()

    # Wait until all items in queue are processed
    buf.join()

    # Stop consumers
    stop_event.set()

    # Wait for consumers to exit
    for t in consumers: t.join(timeout=2.0)

    # Return collected statistics
    return dict(stats)


# ---------------- DIVIDER (for formatting output) ----------------
def divider(title="", width=70):
    ch = "─"
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{ch*pad} {BOLD}{title}{RESET} {ch*(width - pad - len(title) - 2)}\n")
    else:
        print(ch * width)


# ---------------- SAFE INTEGER INPUT ----------------
def get_int(prompt, lo, hi, default):
    while True:
        try:
            raw = input(f"  {prompt} [{lo}-{hi}, default={default}]: ").strip()
            if raw == "": return default
            val = int(raw)
            if lo <= val <= hi: return val
            print(f"  Please enter a number between {lo} and {hi}.")
        except ValueError:
            print("  Please enter a valid number.")


# ---------------- MENU FUNCTION ----------------
def menu():

    # Display main menu
    print(f"\n{'='*70}")
    print(f"  {BOLD}{GREEN}Food Delivery System — Producer-Consumer Simulation{RESET}")
    print(f"  {'='*68}")
    print(f"  {DIM}Restaurants place orders  →  shared queue  →  riders deliver{RESET}")
    print(f"{'='*70}\n")

    print(f"  {BOLD}1{RESET}  Part A — Bounded Buffer")
    print(f"  {BOLD}2{RESET}  Part B — Unbounded Buffer")
    print(f"  {BOLD}3{RESET}  Compare Both")
    print(f"  {BOLD}0{RESET}  Exit\n")

    # Get user choice
    choice = input("  Your choice: ").strip()

    # Exit program
    if choice == "0":
        print("\n  Goodbye!\n")
        return

    # Invalid input handling
    if choice not in ("1", "2", "3"):
        print("  Invalid choice.")
        input("  Press Enter to try again…")
        menu()
        return

    # Take user inputs
    n_prod   = get_int("Number of restaurants (producers)", 1, 6, 2)
    n_cons   = get_int("Number of riders (consumers)", 1, 6, 2)
    n_orders = get_int("Orders each restaurant will place", 1, 20, 6)

    # Run selected option
    if choice == "1":
        result = run_simulation("bounded", n_prod, n_cons, n_orders)

    elif choice == "2":
        result = run_simulation("unbounded", n_prod, n_cons, n_orders)

    elif choice == "3":
        res_b = run_simulation("bounded", n_prod, n_cons, n_orders)
        res_u = run_simulation("unbounded", n_prod, n_cons, n_orders)

    input("  Press Enter to return to the menu…")
    menu()


# ---------------- PROGRAM START ----------------
if __name__ == "__main__":
    menu()