import sys
from distributed_allocator import CoordinatorService

def main():
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5000
    
    coordinator = CoordinatorService(port=port)
    
    try:
        coordinator.start()
        print("Press Ctrl+C to stop")
        while True:
            pass
    except KeyboardInterrupt:
        coordinator.stop()
        print("Coordinator stopped")

if __name__ == '__main__':
    main()
