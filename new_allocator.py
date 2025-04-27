from server import Server
from vm import VM
from config import LIMIT_RATIO, POOL

def try_allocate_to_existing(servers, vm):
    """Try to allocate a VM to any existing server."""
    for server in servers:
        if server.allocate_vm(vm, LIMIT_RATIO):
            return True
    return False

# Original greedy algorithm with reassignment and fixed pool
def greedy_allocate(servers: list[Server], new_vm: VM):
    # Try to allocate to existing servers first
    if try_allocate_to_existing(servers, new_vm):
        return True
    
    # Try reassignment
    vm_mappings = []
    for server in servers:
        for vm in server.allocated:
            vm_mappings.append((server, vm))
    
    for server, vm in vm_mappings:
        server.remove_vm(vm)
        
        if try_allocate_to_existing(servers, new_vm):
            if try_allocate_to_existing(servers, vm):
                return True
            
            # If we can't allocate the original VM, restore state
            for s in servers:
                if new_vm in s.allocated:
                    s.remove_vm(new_vm)
                    break
            
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