from server import Server
from vm import VM
from new_allocator import (
    greedy_allocate, 
    first_fit_allocate, 
    best_fit_allocate, 
    next_fit_allocate,
    weight_balanced_allocate,
    best_fit_epsilon_greedy_allocate,
    delayed_bin_packing_allocate
)
from config import DEFAULT_SERVER_CAPACITY, POOL


def print_servers(servers):
    print("\nCurrent Server States:")
    for i, s in enumerate(servers):
        print(f"S{i + 1}: {s}")


def main():
    # Create a fixed pool of servers upfront
    servers = [Server(DEFAULT_SERVER_CAPACITY) for _ in range(POOL)]
    last_used_index = 0  # For next-fit algorithm
    
    print("Select allocation algorithm:")
    print("1. Original Greedy (with reassignment)")
    print("2. First Fit")
    print("3. Best Fit")
    print("4. Next Fit")
    print("5. Weight Balanced")
    print("6. Epsilon Greedy Best Fit")
    print("7. Delayed Bin Packing")
    print(f"\nFixed Server Pool Size: {POOL}")
    
    try:
        algorithm = int(input("Select algorithm (1-7): "))
        if algorithm not in range(1, 8):
            print("Invalid selection, defaulting to Best Fit (3)")
            algorithm = 3
    except ValueError:
        print("Invalid input, defaulting to Best Fit (3)")
        algorithm = 3
    
    algorithm_names = {
        1: "Original Greedy",
        2: "First Fit",
        3: "Best Fit", 
        4: "Next Fit",
        5: "Weight Balanced",
        6: "Best Fit Epsilon Greedy",
        7: "Delayed Bin Packing"
    }
    
    print(f"\nUsing {algorithm_names[algorithm]} allocation strategy")
    print("Enter memory requirements for VMs (type 'exit' to stop):")
    
    while True:
        entry = input("New VM > ")
        if entry.lower() == 'exit':
            break
        try:
            mem = int(entry)
            vm = VM(mem)
            
            # Apply the selected allocation algorithm
            success = False
            
            if algorithm == 1:
                success = greedy_allocate(servers, vm)
            elif algorithm == 2:
                success = first_fit_allocate(servers, vm)
            elif algorithm == 3:
                success = best_fit_allocate(servers, vm)
            elif algorithm == 4:
                last_used_index, success = next_fit_allocate(servers, vm, last_used_index)
            elif algorithm == 5:
                success = weight_balanced_allocate(servers, vm)
            elif algorithm == 6:
                success = best_fit_epsilon_greedy_allocate(servers,vm)
            elif algorithm == 7:
                success = delayed_bin_packing_allocate(servers,vm)
            if success:
                print(f"Successfully allocated VM({mem})")
            else:
                print(f"ERROR: Could not allocate VM({mem}) - insufficient resources in the server pool")
            
            print_servers(servers)
        except ValueError:
            print("Invalid input. Please enter an integer.")


if __name__ == '__main__':
    main()