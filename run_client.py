import sys
import time
from distributed_allocator import Client

def print_servers(server_status):
    servers = server_status.get('servers', [])
    if not servers:
        print("\nNo servers available or unable to fetch server status")
        return
        
    print("\nCurrent Server States:")
    for i, server in enumerate(servers):
        print(f"S{i+1}: {server['ip']} - Capacity: {server['capacity']}, "
              f"Used: {server['used']}, Free: {server['free']}, "
              f"Active: {'Yes' if server['active'] else 'No'}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_client.py <coordinator_ip> [algorithm]")
        return
    
    coordinator_ip = sys.argv[1]
    algorithm = sys.argv[2] if len(sys.argv) > 2 else 'best_fit'
    
    client = Client(coordinator_ip)
    
    print(f"Using {algorithm} allocation strategy")
    print("Enter memory requirements for VMs (type 'exit' to stop, 'status' to see servers):")
    
    #initial server status
    print("Connecting to coordinator...")
    status = client.get_server_status()
    print_servers(status)
    
    while True:
        try:
            entry = input("New VM > ")
            if entry.lower() == 'exit':
                break
            elif entry.lower() == 'status':
                status = client.get_server_status()
                print_servers(status)
            else:
                try:
                    mem = int(entry)
                    print(f"Requesting allocation of VM({mem})...")
                    success = client.allocate_vm(mem, algorithm)
                    
                    if success:
                        print(f"Successfully allocated VM({mem})")
                    else:
                        print(f"ERROR: Could not allocate VM({mem}) - insufficient resources in the server pool")
                    
                    # Give a short delay for status to update across the network
                    time.sleep(1)
                    status = client.get_server_status()
                    print_servers(status)
                except ValueError:
                    print("Invalid input. Please enter an integer.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    main()
