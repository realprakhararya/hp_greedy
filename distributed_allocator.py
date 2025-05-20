# distributed_allocator.py
import socket
import json
import threading
import time
from server import Server
from vm import VM
from config import DEFAULT_SERVER_CAPACITY, LIMIT_RATIO
from new_allocator import best_fit_allocate, weight_balanced_allocate

class NetworkServer(Server):
    def __init__(self, capacity, ip_address, port=5000):
        # if None is encountered
        if capacity is None:
            capacity = DEFAULT_SERVER_CAPACITY
        super().__init__(capacity)
        self.ip_address = ip_address
        self.port = port
        self.last_heartbeat = time.time()
        self.is_active = True
    
    def __repr__(self):
        return f"NetworkServer(IP: {self.ip_address}, Capacity: {self.capacity}, Used: {self.used_memory()}, Free: {self.free_space()})"

    # Directly allocate on the actual server
    def remote_allocate_vm(self, vm):
        """Allocate a VM on the remote server"""
        try:
            message = {
                'type': 'allocate_vm',
                'memory': vm.memory
            }
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.ip_address, self.port))
                s.send(json.dumps(message).encode('utf-8'))
                
                data = s.recv(4096).decode('utf-8')
                if not data:
                    print(f"Empty response from remote server {self.ip_address}")
                    return False
                    
                try:
                    response = json.loads(data)
                    success = response.get('status') == 'allocated'
                    if success:
                        # Update our local model of the server
                        self.allocated.append(vm)
                    return success
                except json.JSONDecodeError:
                    return False
        except Exception as e:
            print(f"Error allocating VM remotely on {self.ip_address}: {e}")
            return False


class CoordinatorService:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.servers = {}  # Dictionary of ip_address: NetworkServer
        self.server_lock = threading.Lock()
        self.running = False
        self.heartbeat_timeout = 10  # seconds

    def start(self):
        """Start the coordinator service"""
        self.running = True
        
        # Start server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        # Start threads for services
        threading.Thread(target=self._accept_connections, daemon=True).start()
        threading.Thread(target=self._monitor_servers, daemon=True).start()
        
        print(f"Coordinator started on {self.host}:{self.port}")
    
    def stop(self):
        """Stop the coordinator service"""
        self.running = False
        self.server_socket.close()
    
    def _accept_connections(self):
        """Accept incoming connections from servers and clients"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_connection, 
                                args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
    
    def _handle_connection(self, client_socket, addr):
        """Handle an incoming connection"""
        try:
            # Itimeout for reliability, std practice
            client_socket.settimeout(5.0)
            data = client_socket.recv(4096).decode('utf-8')
            
            if not data:
                print(f"Empty data received from {addr}")
                return
                
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON from {addr}: {data[:100]}... Error: {e}")
                client_socket.send(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode('utf-8'))
                return
            
            if message['type'] == 'register':
                self._register_server(message, addr)
                response = {'status': 'registered'}
            
            elif message['type'] == 'heartbeat':
                self._update_heartbeat(message)
                response = {'status': 'ok'}
            
            elif message['type'] == 'allocate_vm':
                success = self._allocate_vm(message)
                response = {'status': 'allocated' if success else 'failed'}
            
            elif message['type'] == 'server_status':
                response = self._get_server_status()
            
            elif message['type'] == 'sync_vms':
                response = self._get_all_vms()
            
            else:
                response = {'status': 'unknown_command'}
            
            # sending out response
            client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Error handling connection from {addr}: {e}")
            try:
                client_socket.send(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()
    
    def _register_server(self, message, addr):
        """Register a new server in the pool"""
        ip = message.get('ip', addr[0])
        capacity = message.get('capacity', DEFAULT_SERVER_CAPACITY)
        port = message.get('port', 5001)
        
        with self.server_lock:
            self.servers[ip] = NetworkServer(capacity, ip, port)
            print(f"Registered server: {ip} with capacity {capacity}")
    
    def _update_heartbeat(self, message):
        """Update the heartbeat timestamp for a server"""
        ip = message.get('ip')
        allocated_vms = message.get('allocated_vms', [])
        
        with self.server_lock:
            if ip in self.servers:
                self.servers[ip].last_heartbeat = time.time()
                
                # vm allocation updated
                self.servers[ip].allocated = [VM(mem) for mem in allocated_vms]
                print(f"Updated heartbeat for {ip} with {len(allocated_vms)} VMs: {allocated_vms}")
            else:
                # re-register if server not found
                capacity = message.get('capacity', DEFAULT_SERVER_CAPACITY)
                port = message.get('port', 5001)
                self.servers[ip] = NetworkServer(capacity, ip, port)
                self.servers[ip].allocated = [VM(mem) for mem in allocated_vms]
                print(f"Re-registered server: {ip} with capacity {capacity}")
    
    def _monitor_servers(self):
        """Monitor server heartbeats and remove inactive servers"""
        while self.running:
            with self.server_lock:
                current_time = time.time()
                to_remove = []
                
                for ip, server in self.servers.items():
                    if current_time - server.last_heartbeat > self.heartbeat_timeout:
                        server.is_active = False
                        to_remove.append(ip)
                
                for ip in to_remove:
                    print(f"Server {ip} timed out, removing from pool")
                    del self.servers[ip]
            
            time.sleep(2)
    
    def _allocate_vm(self, message):
        """Allocate a VM to one of the servers in the pool"""
        memory = message.get('memory')
        algorithm = message.get('algorithm', 'best_fit')
        vm = VM(memory)
        
        with self.server_lock:
            active_servers = [s for s in self.servers.values() if s.is_active]
            
            if not active_servers:
                print("No active servers available for allocation")
                return False
            
            print(f"Attempting to allocate VM({memory}) using {algorithm}")
            
            # find the best server based on the algorithm
            chosen_server = None
            
            if algorithm == 'best_fit':
                # Find the best fitting server without actually allocating
                min_remaining = float('inf')
                for server in active_servers:
                    if server.can_allocate(vm, LIMIT_RATIO):
                        remaining = server.free_space() - vm.size()
                        if remaining < min_remaining:
                            min_remaining = remaining
                            chosen_server = server
            
            elif algorithm == 'weight_balanced':
                # Find the best server by score without actually allocating
                best_score = float('-inf')
                for server in active_servers:
                    if server.can_allocate(vm, LIMIT_RATIO):
                        current_utilization = server.used_memory() / server.capacity
                        new_utilization = (server.used_memory() + vm.size()) / server.capacity
                        score = 1 - abs(new_utilization - 0.75)
                        
                        if score > best_score:
                            best_score = score
                            chosen_server = server
            
            else:  # First fit
                for server in active_servers:
                    if server.can_allocate(vm, LIMIT_RATIO):
                        chosen_server = server
                        break
            
            # If we found a suitable server, remotely allocate the VM there
            if chosen_server:
                print(f"Selected server {chosen_server.ip_address} for VM({memory})")
                # Actually allocate on the remote server
                return chosen_server.remote_allocate_vm(vm)
            
            return False
    
    def _get_server_status(self):
        """Get the status of all servers"""
        with self.server_lock:
            return {
                'servers': [
                    {
                        'ip': server.ip_address,
                        'capacity': server.capacity,
                        'used': server.used_memory(),
                        'free': server.free_space(),
                        'active': server.is_active
                    }
                    for server in self.servers.values()
                ]
            }
    
    def _get_all_vms(self):
        """Get all VMs allocated across all servers"""
        with self.server_lock:
            all_vms = []
            for server in self.servers.values():
                if server.is_active:
                    for vm in server.allocated:
                        all_vms.append({
                            'server_ip': server.ip_address,
                            'memory': vm.memory
                        })
            return {'vms': all_vms}


class ServerAgent:
    def __init__(self, coordinator_host, coordinator_port=5000, 
                 server_port=5001, capacity=None):
        self.coordinator_host = coordinator_host
        self.coordinator_port = coordinator_port
        self.server_port = server_port
        
        # Fix the None capacity issue
        if capacity is None:
            capacity = DEFAULT_SERVER_CAPACITY
        self.capacity = capacity
        
        self.server = Server(capacity)
        self.running = False
        
        # Get our own IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            self.ip_address = s.getsockname()[0]
        except Exception:
            self.ip_address = '127.0.0.1'
        finally:
            s.close()
    
    def start(self):
        """Start the server agent"""
        self.running = True
        
        # eegister with coordinator
        self._register()
        
        # sync VMs from coordinator
        self._sync_vms()
        
        # start heartbeat thread, to check the connectivity with different pcs
        threading.Thread(target=self._send_heartbeat, daemon=True).start()
        
        # start server socket to accept VM allocations
        threading.Thread(target=self._start_server, daemon=True).start()
        
        print(f"Server agent started on {self.ip_address}:{self.server_port} with capacity {self.capacity}")
    
    def stop(self):
        """Stop the server agent"""
        self.running = False
    
    def _register(self):
        """Register this server with the coordinator"""
        message = {
            'type': 'register',
            'ip': self.ip_address,
            'port': self.server_port,
            'capacity': self.capacity
        }
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)  # Set timeout for socket operations
                s.connect((self.coordinator_host, self.coordinator_port))
                s.send(json.dumps(message).encode('utf-8'))
                
                data = s.recv(4096).decode('utf-8')
                if not data:
                    print("Empty response from coordinator during registration")
                    return
                    
                try:
                    response = json.loads(data)
                    
                    if response.get('status') == 'registered':
                        print(f"Successfully registered with coordinator")
                    else:
                        print(f"Failed to register with coordinator: {response}")
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from coordinator during registration: {data[:100]}... Error: {e}")
        except Exception as e:
            print(f"Error registering with coordinator: {e}")
    
    def _sync_vms(self):
        """Sync VMs that belong to this server from the coordinator"""
        message = {'type': 'sync_vms'}
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.coordinator_host, self.coordinator_port))
                s.send(json.dumps(message).encode('utf-8'))
                
                data = s.recv(4096).decode('utf-8')
                if not data:
                    print("Empty response from coordinator during VM sync")
                    return
                
                try:
                    response = json.loads(data)
                    vms = response.get('vms', [])
                    
                    # Reset server's VMs
                    self.server.clear()
                    
                    # Add VMs that belong to this server
                    for vm_info in vms:
                        if vm_info['server_ip'] == self.ip_address:
                            vm = VM(vm_info['memory'])
                            self.server.allocate_vm(vm, LIMIT_RATIO)
                    
                    print(f"Synced {len(self.server.allocated)} VMs from coordinator")
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from coordinator during VM sync: {data[:100]}... Error: {e}")
        except Exception as e:
            print(f"Error syncing VMs from coordinator: {e}")
    
    def _send_heartbeat(self):
        """Send heartbeat to coordinator periodically"""
        while self.running:
            try:
                message = {
                    'type': 'heartbeat',
                    'ip': self.ip_address,
                    'capacity': self.capacity,
                    'port': self.server_port,
                    'allocated_vms': [vm.memory for vm in self.server.allocated]
                }
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5.0)  # Set timeout for socket operations
                    s.connect((self.coordinator_host, self.coordinator_port))
                    s.send(json.dumps(message).encode('utf-8'))
                    
                    # More robust response handling
                    try:
                        data = s.recv(4096).decode('utf-8')
                        if data:  # Only try to parse if we got data
                            response = json.loads(data)
                    except:
                        pass  # Silently ignore heartbeat acknowledgment issues
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
            
            time.sleep(5)
    
    def _start_server(self):
        """Start a server socket to accept VM allocation requests"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.ip_address, self.server_port))
            server_socket.listen(5)
            
            while self.running:
                try:
                    client_socket, addr = server_socket.accept()
                    threading.Thread(target=self._handle_client, 
                                    args=(client_socket, addr), daemon=True).start()
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
        finally:
            server_socket.close()
    
    def _handle_client(self, client_socket, addr):
        """Handle a client connection for VM allocation"""
        try:
            client_socket.settimeout(5.0)  # Set timeout
            data = client_socket.recv(4096).decode('utf-8')
            
            if not data:
                print(f"Empty data received from {addr}")
                return
                
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON from {addr}: {data[:100]}... Error: {e}")
                client_socket.send(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode('utf-8'))
                return
            
            if message['type'] == 'allocate_vm':
                memory = message['memory']
                vm = VM(memory)
                success = self.server.allocate_vm(vm, LIMIT_RATIO)
                
                response = {'status': 'allocated' if success else 'failed'}
                print(f"VM allocation request: {memory} - {'Success' if success else 'Failed'}")
            elif message['type'] == 'server_status':
                response = {
                    'capacity': self.server.capacity,
                    'used': self.server.used_memory(),
                    'free': self.server.free_space(),
                    'vms': [vm.memory for vm in self.server.allocated]
                }
            else:
                response = {'status': 'unknown_command'}
            
            client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            try:
                client_socket.send(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()


class Client:
    def __init__(self, coordinator_host, coordinator_port=5000):
        self.coordinator_host = coordinator_host
        self.coordinator_port = coordinator_port
    
    def allocate_vm(self, memory, algorithm='best_fit'):
        """Request VM allocation from the coordinator"""
        message = {
            'type': 'allocate_vm',
            'memory': memory,
            'algorithm': algorithm
        }
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)  # Set timeout for socket operations
                s.connect((self.coordinator_host, self.coordinator_port))
                s.send(json.dumps(message).encode('utf-8'))
                
                data = s.recv(4096).decode('utf-8')
                if not data:
                    print("Empty response from coordinator")
                    return False
                    
                try:
                    response = json.loads(data)
                    return response.get('status') == 'allocated'
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from coordinator: {data[:100]}... Error: {e}")
                    return False
        except Exception as e:
            print(f"Error allocating VM: {e}")
            return False
    
    def get_server_status(self):
        """Get status of all servers from the coordinator"""
        message = {'type': 'server_status'}
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)  # Set timeout for socket operations
                s.connect((self.coordinator_host, self.coordinator_port))
                s.send(json.dumps(message).encode('utf-8'))
                
                data = s.recv(4096).decode('utf-8')
                if not data:
                    print("Empty response from coordinator")
                    return {'servers': []}
                    
                try:
                    response = json.loads(data)
                    return response
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from coordinator: {data[:100]}... Error: {e}")
                    return {'servers': []}
        except Exception as e:
            print(f"Error getting server status: {e}")
            return {'servers': []}