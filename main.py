from server import Server
from vm import VM
from allocator import greedy_allocate
from config import DEFAULT_SERVER_CAPACITY


def print_servers(servers):
    print("\nCurrent Server States:")
    for i, s in enumerate(servers):
        print(f"S{i + 1}: {s}")


def main():
    servers = [Server(DEFAULT_SERVER_CAPACITY)]

    print("Enter CPU requirements for VMs (type 'exit' to stop):")
    while True:
        entry = input("New VM > ")
        if entry.lower() == 'exit':
            break
        try:
            mem = int(entry)
            vm = VM(mem)
            servers = greedy_allocate(servers, vm)
            print_servers(servers)
        except ValueError:
            print("Invalid input. Please enter an integer.")


if __name__ == '__main__':
    main()
