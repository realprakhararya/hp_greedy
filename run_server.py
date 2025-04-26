import sys
from distributed_allocator import ServerAgent
from config import DEFAULT_SERVER_CAPACITY

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_server.py <coordinator_ip> [port] [capacity]")
        return
    
    coordinator_ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001
    
    # Handle capacity explicitly
    if len(sys.argv) > 3:
        capacity = int(sys.argv[3])
    else:
        capacity = DEFAULT_SERVER_CAPACITY
        print(f"Using default capacity: {capacity}")
    
    agent = ServerAgent(coordinator_ip, 5000, port, capacity)
    
    try:
        agent.start()
        print("Press Ctrl+C to stop")
        while True:
            pass
    except KeyboardInterrupt:
        agent.stop()
        print("Server agent stopped")

if __name__ == '__main__':
    main()
