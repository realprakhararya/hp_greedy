# HP Greedy – VM Placement and Migration (Preliminary Version)

This repository contains the **preliminary implementation** of a VM placement and migration algorithm.  
It forms the **foundation** for the later version built with **Flask REST endpoints** and **libvirt calls over KVM** for automated VM provisioning and live migration on physical servers.

---

## 🖥️ Overview

The project explores **heuristic-based placement and migration of Virtual Machines (VMs)** across physical hosts, focusing on resource optimization and efficient utilization.  

For this stage, the implementation is simulation-oriented and **does not include libvirt integration or REST APIs**. Instead, it demonstrates the **core greedy algorithm** used to allocate VMs to hosts based on available resources.This repository represents the preliminary open-source version. The production-ready KVM + libvirt implementation has been pivoted to a private repository to ensure safe infrastructure handling and maintaining compliance guildlines.

---

## ✨ Features (Preliminary)

- **Greedy Allocation Algorithm** → Places VMs onto hosts by checking resource constraints.  
- **Simulation Environment** → Models physical hosts and VM demands in Python.  
- **Resource Tracking** → Monitors CPU and memory utilization.  
- **Basis for KVM Integration** → Provides the logic later extended with libvirt + Flask API.  

---

## 🚀 Run the project


Start the coordinator on one machine, which will act as the host:

```python run_coordinator.py``` 

Start the servers on the nodes (you can even use the host as a node as well)

```python run_server.py <ip_address_of_host> <port_no> <memory>```

Run the client module to enter the memory of the vms you are allocating, you can run it 

```python run_client.py <ip_address)of_host> <algo_name>```

## 📊 Example Input (which forms basiss for JSON parsing for the KVM implementation)

```
{
  "hosts": [
    {"id": 1, "cpu": 32, "memory": 128},
    {"id": 2, "cpu": 16, "memory": 64}
  ],
  "vms": [
    {"id": "vm1", "cpu": 4, "memory": 8},
    {"id": "vm2", "cpu": 8, "memory": 16}
  ]
}
```
