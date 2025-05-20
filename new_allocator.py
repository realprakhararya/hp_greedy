from server import Server
from vm import VM
from config import LIMIT_RATIO, POOL
import random
from collections import deque

def try_allocate_to_existing(servers, vm):
    """Try to allocate a VM to any existing server."""
    for server in servers:
        if server.allocate_vm(vm, LIMIT_RATIO):
            return True
    return False

def greedy_allocate(servers: list[Server], new_vm: VM):
    # allocate to existing servers first if possible
    if try_allocate_to_existing(servers, new_vm):
        return True
    
    # Try reassignment
    vm_mappings = []
    for server in servers:
        for vm in server.allocated:
            vm_mappings.append((server, vm))
    
    for server, vm in vm_mappings:
        # Remove the original VM
        server.remove_vm(vm)
        
        # Try to allocate the new VM
        new_vm_server = None
        for s in servers:
            if s.can_allocate(new_vm):
                s.allocate_vm(new_vm)
                new_vm_server = s
                break
        
        if new_vm_server:
            # Try to allocate the original VM somewhere
            if try_allocate_to_existing(servers, vm):
                return True
            new_vm_server.remove_vm(new_vm)
        server.allocate_vm(vm)
    
    # If we reach here, we couldn't allocate even with reassignment
    return False

# First Fit algorithm with fixed pool
def first_fit_allocate(servers: list[Server], new_vm: VM):
    """
    First Fit allocation - places the VM in the first server that can accommodate it.
    Returns success indicating if allocation was possible.
    """
    # Try to allocate to the first server with enough space
    for server in servers:
        if server.allocate_vm(new_vm, LIMIT_RATIO):
            return True
    
    # If no suitable server found
    return False

# Best Fit algorithm with fixed pool
def best_fit_allocate(servers: list[Server], new_vm: VM):
    """
    Best Fit allocation - places the VM in the server that leaves the least remaining space.
    Returns success indicating if allocation was possible.
    """
    best_server = None
    min_remaining = float('inf')
    
    # Find the server with the least remaining space that can fit the VM
    for server in servers:
        if server.can_allocate(new_vm, LIMIT_RATIO):
            remaining = server.free_space() - new_vm.size()
            if remaining < min_remaining:
                min_remaining = remaining
                best_server = server
    
    # If a suitable server was found, allocate the VM there
    if best_server:
        best_server.allocate_vm(new_vm, LIMIT_RATIO)
        return True
    
    # If no suitable server found
    return False

# Next Fit algorithm with fixed pool
def next_fit_allocate(servers: list[Server], new_vm: VM, last_used_index=None):
    """
    Next Fit allocation - places the VM in the last used server or the next available one.
    Returns (last_used_index, success) where success indicates if allocation was possible.
    """
    if last_used_index is None or last_used_index >= len(servers):
        last_used_index = 0
    
    # Start checking from the last used server
    start_idx = last_used_index
    current_idx = start_idx
    
    # Try all servers starting from the last used one
    checked_count = 0
    while checked_count < len(servers):
        if servers[current_idx].allocate_vm(new_vm, LIMIT_RATIO):
            return current_idx, True
        
        current_idx = (current_idx + 1) % len(servers)
        checked_count += 1
    
    # If no suitable server found
    return last_used_index, False

# Weight-based algorithm with fixed pool
def weight_balanced_allocate(servers: list[Server], new_vm: VM):
    """
    Allocates VMs using a weight-based approach that balances
    between minimizing the number of servers and balancing load.
    Returns success indicating if allocation was possible.
    """
    best_server = None
    best_score = float('-inf')
    
    # Calculate a score for each server
    for server in servers:
        if server.can_allocate(new_vm, LIMIT_RATIO):
            # Score balances between filling servers efficiently and load balancing
            # Higher utilization but not too high is preferred
            current_utilization = server.used_memory() / server.capacity
            new_utilization = (server.used_memory() + new_vm.size()) / server.capacity
            
            # Prefer servers that won't be too empty or too full after allocation
            # The closer to 75% utilization, the better the score
            score = 1 - abs(new_utilization - 0.75)
            
            if score > best_score:
                best_score = score
                best_server = server
    
    # If a suitable server was found, allocate the VM there
    if best_server:
        best_server.allocate_vm(new_vm, LIMIT_RATIO)
        return True
    
    # If no suitable server found
    return False
def best_fit_epsilon_greedy_allocate(servers: list[Server], new_vm: VM, epsilon: float = 0.7):
    """
    Epsilon-Greedy Best Fit allocation:
    - With probability (1-epsilon): Chooses best-fit server (minimizes remaining space)
    - With probability epsilon: Randomly selects any valid server
    Returns True if allocation succeeded, False otherwise
    """
    # Find all servers that can accommodate the VM
    valid_servers = [s for s in servers if s.can_allocate(new_vm, LIMIT_RATIO)]
    
    if not valid_servers:
        return False  # No servers can accommodate this VM

    # With probability epsilon, explore (choose random valid server)
    if random.random() < epsilon:
        chosen_server = random.choice(valid_servers)
        print("Allocating randomly:")
        return chosen_server.allocate_vm(new_vm, LIMIT_RATIO)
    
    # Otherwise exploit (use best-fit strategy)
    best_server = None
    min_remaining = float('inf')
    
    for server in valid_servers:
        remaining = server.free_space() - new_vm.size()
        if remaining < min_remaining:
            min_remaining = remaining
            best_server = server
    
    if best_server:
        print("Allocating best fit:")
        return best_server.allocate_vm(new_vm, LIMIT_RATIO)
    
    return False  # Should never reach here if valid_servers isn't empty

def delayed_bin_packing_allocate(servers: list[Server], new_vm: VM, wait_k=3):
    """
    Delayed bin packing with 2-sum matching:
    1. First tries to match with existing server's exact remaining capacity
    2. Then tries to match with waiting VMs that sum to server capacity
    3. Otherwise holds VM in queue until wait threshold is reached
    """
    # Convert servers to remaining capacities
    remaining = [s.free_space() for s in servers]
    waiting_queue = deque()  # Stores (vm, wait_count)
    
    # Static variable to maintain queue across calls
    if not hasattr(delayed_bin_packing_allocate, "global_waiting_queue"):
        delayed_bin_packing_allocate.global_waiting_queue = deque()
    waiting_queue = delayed_bin_packing_allocate.global_waiting_queue
    
    # Step 1: Try exact remaining match
    for i, rem in enumerate(remaining):
        if rem == new_vm.size():
            if servers[i].allocate_vm(new_vm, LIMIT_RATIO):
                return True
    
    # Step 2: Try 2-sum match with waiting VMs
    for idx, (waiting_vm, _) in enumerate(waiting_queue):
        if new_vm.size() + waiting_vm.size() == servers[0].capacity:  # All servers same capacity
            # Find a server that can fit both
            for server in servers:
                if server.can_allocate(new_vm, LIMIT_RATIO) and server.can_allocate(waiting_vm, LIMIT_RATIO):
                    server.allocate_vm(new_vm, LIMIT_RATIO)
                    server.allocate_vm(waiting_vm, LIMIT_RATIO)
                    del waiting_queue[idx]
                    return True
    
    # Step 3: Add to waiting queue
    waiting_queue.append((new_vm, 0))
    
    # Step 4: Process waiting queue
    updated_queue = deque()
    for vm, wait_count in waiting_queue:
        wait_count += 1
        if wait_count >= wait_k:
            # First Fit allocation for waited-too-long VMs
            for server in servers:
                if server.can_allocate(vm, LIMIT_RATIO):
                    server.allocate_vm(vm, LIMIT_RATIO)
                    break
            else:
                return False  # Couldn't allocate even after waiting
        else:
            updated_queue.append((vm, wait_count))
    
    delayed_bin_packing_allocate.global_waiting_queue = updated_queue
    return True  # Holding in queue counts as temporary success