Start the coordinator on one machine, which will act as the host:

```python run_coordinator.py``` 

Start the servers on the nodes (you can even use the host as a node as well)

```python run_server.py <ip_address_of_host> <port_no> <memory>```

Run the client module to enter the memory of the vms you are allocating, you can run it 

```python run_client.py <ip_address)of_host> <algo_name>```
