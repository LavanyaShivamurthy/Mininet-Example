#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
import time
from time import sleep
import threading
import json
from collections import defaultdict
import psutil
import subprocess
import csv
from datetime import datetime

def generate_emergency_alerts(host, destination, duration=60):
    """Generate emergency alert traffic"""
    while True:
        # Small packets (100 bytes) with highest priority
        host.cmd(f'ping -c 1 -s 100 -Q 0x28 {destination} &')
        time.sleep(random.uniform(0.5, 2.0))  # Random intervals

def generate_patient_monitoring(host, destination, duration=60):
    """Generate continuous patient monitoring data"""
    # Use iperf for continuous stream with specific QoS
    host.cmd(f'iperf -c {destination} -t {duration} -u -b 2M -Q 0x20 &')

def generate_medical_imaging(host, destination, duration=60):
    """Generate large medical imaging data"""
    # Large data transfer with high bandwidth
    host.cmd(f'iperf -c {destination} -t {duration} -b 50M -Q 0x18 &')

class TCPDumpCollector:
    def __init__(self, net, output_dir='tcpdump_data'):
        self.net = net
        self.output_dir = output_dir
        self.processes = {}
        os.makedirs(output_dir, exist_ok=True)
    
    def start_capture(self, node, interface=None, filter_str=None):
        """Start tcpdump capture on a node"""
        if isinstance(node, str):
            node = self.net.get(node)
        
        # If no interface specified, capture on all interfaces
        if interface is None:
            interfaces = [intf.name for intf in node.intfs.values() if intf.name != 'lo']
        else:
            interfaces = [interface]
        
        for intf in interfaces:
            try:
                # Create filename based on node, interface and timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{self.output_dir}/{node.name}_{intf}_{timestamp}.pcap'
                
                # Build tcpdump command using pgrep to get PID reliably
                cmd = f'tcpdump -i {intf} -w {filename}'
                if filter_str:
                    cmd += f' "{filter_str}"'
                
                # Start tcpdump in background
                node.cmd(f'{cmd} > /dev/null 2>&1 &')
                
                # Get PID using pgrep
                pid_output = node.cmd(f"pgrep -f 'tcpdump -i {intf}'")
                
                # Extract PID from output
                try:
                    pid = int(pid_output.strip().split('\n')[0])
                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not get PID for tcpdump on {node.name} {intf}, using placeholder")
                    pid = -1
                
                self.processes[(node.name, intf)] = {
                    'pid': pid,
                    'file': filename
                }
                print(f"Started tcpdump on {node.name} interface {intf}, saving to {filename} (PID: {pid})")
                
            except Exception as e:
                print(f"Error starting tcpdump on {node.name} interface {intf}: {e}")
    
    def stop_capture(self, node=None, interface=None):
        """Stop tcpdump capture"""
        if node:
            if isinstance(node, str):
                node_name = node
            else:
                node_name = node.name
            
            # Stop specific interface or all interfaces for the node
            to_stop = [(n, i) for n, i in self.processes.keys() 
                      if n == node_name and (interface is None or i == interface)]
        else:
            # Stop all captures
            to_stop = list(self.processes.keys())
        
        for node_name, intf in to_stop:
            try:
                process = self.processes.pop((node_name, intf))
                node = self.net.get(node_name)
                
                # Kill tcpdump process more reliably
                if process['pid'] != -1:
                    node.cmd(f'kill {process["pid"]}')
                
                # Backup method to ensure tcpdump is stopped
                node.cmd(f"pkill -f 'tcpdump -i {intf}'")
                
                print(f"Stopped tcpdump on {node_name} interface {intf}")
                print(f"Capture saved to {process['file']}")
                
            except Exception as e:
                print(f"Error stopping tcpdump on {node_name} interface {intf}: {e}")
    
    def cleanup(self):
        """Cleanup all tcpdump processes"""
        try:
            # Stop all captures
            self.stop_capture()
            
            # Additional cleanup to ensure no tcpdump processes remain
            for node in self.net.hosts:
                node.cmd('pkill -f tcpdump')
            
            print("Cleaned up all tcpdump processes")
            
        except Exception as e:
            print(f"Error during tcpdump cleanup: {e}")

def createHealthcareNetwork():
    net = Mininet(topo=None, build=False, link=TCLink)
    info('*** Adding controller\n')
    c0 = net.addController('c0')

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)

    info('*** Adding medical devices/hosts\n')
    # Emergency Alert Devices
    emergency = net.addHost('emergency', ip='10.0.0.10')
    # Patient Monitoring Devices
    monitoring = net.addHost('monitoring', ip='10.0.0.20')
    # Medical Imaging Devices
    imaging = net.addHost('imaging', ip='10.0.0.30')
    # Medical Device Host
    med_device = net.addHost('med_device', ip='10.0.0.40')
    # Administrative System
    admin = net.addHost('admin', ip='10.0.0.50')
    # Environmental Sensors
    env_sensor = net.addHost('env_sensor', ip='10.0.0.60')
    
    # Server to receive all traffic
    server = net.addHost('server', ip='10.0.0.100')

    info('*** Creating links with QoS\n')
    # Links with different bandwidth and latency requirements
    net.addLink(emergency, s1, cls=TCLink, bw=10) #, delay='2ms', max_queue_size=1000)
    net.addLink(monitoring, s1, cls=TCLink, bw=10) # , delay='5ms', max_queue_size=1000)
    net.addLink(imaging, s1, cls=TCLink, bw=10) #, delay='10ms', max_queue_size=1000)
    net.addLink(med_device, s2, cls=TCLink, bw=10)#, delay='20ms', max_queue_size=1000)
    net.addLink(admin, s2, cls=TCLink, bw=10)#, delay='50ms', max_queue_size=1000)
    net.addLink(env_sensor, s2, cls=TCLink, bw=10)#, delay='100ms', max_queue_size=1000)
    net.addLink(server, s3, cls=TCLink, bw=10)#, delay='1ms', max_queue_size=1000)
    
    # Inter-switch links
    net.addLink(s1, s2, cls=TCLink, bw=15, delay='1ms')
    net.addLink(s2, s3, cls=TCLink, bw=15, delay='1ms')

    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    info('*** Configuring QoS\n')
    # Configure QoS queues on switches
    # Queue configuration for s1
    s1.cmd('ovs-vsctl -- set Port s1-eth1 qos=@newqos -- \
            --id=@newqos create QoS type=linux-htb \
            queues=0=@q0,1=@q1,2=@q2,3=@q3,4=@q4,5=@q5 -- \
            --id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=10000000 -- \
            --id=@q1 create Queue other-config:min-rate=5000000 other-config:max-rate=20000000 -- \
            --id=@q2 create Queue other-config:min-rate=10000000 other-config:max-rate=50000000 -- \
            --id=@q3 create Queue other-config:min-rate=5000000 other-config:max-rate=15000000 -- \
            --id=@q4 create Queue other-config:min-rate=2000000 other-config:max-rate=10000000 -- \
            --id=@q5 create Queue other-config:min-rate=1000000 other-config:max-rate=5000000')

"""
    # Flow rules for different traffic types
    # Emergency Alerts (Highest Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=100,ip,nw_src=10.0.0.10,actions=set_queue:0,normal')
    
    # Patient Monitoring (High Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=90,ip,nw_src=10.0.0.20,actions=set_queue:1,normal')
    
    # Medical Imaging (High Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=80,ip,nw_src=10.0.0.30,actions=set_queue:2,normal')
    
    # Medical Devices (Medium-High Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=70,ip,nw_src=10.0.0.40,actions=set_queue:3,normal')
    
    # Administrative (Medium Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=60,ip,nw_src=10.0.0.50,actions=set_queue:4,normal')
    
    # Environmental (Low Priority)
    s1.cmd('ovs-ofctl add-flow s1 priority=50,ip,nw_src=10.0.0.60,actions=set_queue:5,normal')
"""
    info('*** Starting traffic generation\n')
    # Start traffic generators in separate threads
    Thread(target=generate_emergency_alerts, args=(emergency, '10.0.0.100')).start()
    Thread(target=generate_patient_monitoring, args=(monitoring, '10.0.0.100')).start()
    Thread(target=generate_medical_imaging, args=(imaging, '10.0.0.100')).start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    createHealthcareNetwork()
