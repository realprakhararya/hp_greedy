from vm import VM

class Server:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.allocated = []

    def __repr__(self):
        return f"Server(Capacity: {self.capacity}, Used: {self.used_memory()}, Free: {self.free_space()}, VMs: {self.allocated})"

    def used_memory(self):
        return sum(vm.size() for vm in self.allocated)

    def free_space(self):
        return self.capacity - self.used_memory()

    def can_allocate(self, vm: VM, limit_ratio: float = 1.0):
        return vm.size() <= self.capacity * limit_ratio - self.used_memory()

    def allocate_vm(self, vm: VM, limit_ratio: float = 1.0):
        if self.can_allocate(vm, limit_ratio):
            self.allocated.append(vm)
            return True
        return False

    def remove_vm(self, vm: VM):
        self.allocated.remove(vm)

    def clear(self):
        self.allocated.clear()