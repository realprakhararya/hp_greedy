from server import Server
from vm import VM
from config import LIMIT_RATIO

def try_allocate_to_existing(servers, vm):
    for server in servers:
        if server.allocate_vm(vm, LIMIT_RATIO):
            return True
    return False

def greedy_allocate(servers: list[Server], new_vm: VM):
    if try_allocate_to_existing(servers, new_vm):
        return servers
    
    vm_mappings = []
    for server in servers:
        for vm in server.allocated:
            vm_mappings.append((server, vm))
    
    for server, vm in vm_mappings:
        server.remove_vm(vm)
        
        if try_allocate_to_existing(servers, new_vm):
            if try_allocate_to_existing(servers, vm):
                return servers
            
            for s in servers:
                if new_vm in s.allocated:
                    s.remove_vm(new_vm)
                    break
            
        server.allocate_vm(vm)
    
    new_server = Server(servers[0].capacity)
    new_server.allocate_vm(new_vm, LIMIT_RATIO)
    servers.append(new_server)
    return servers