from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import time
from time import sleep
from datetime import datetime
import threading
from numpy import random

import subprocess
import psutil
from mininet.util import dumpNodeConnections
import json
from collections import defaultdict
import csv





class customTopology(Topo):
    def build(self):

        info('*** Adding switches\n')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')

        info('*** Adding medical devices/hosts\n')
        # Emergency Alert Devices
        emergency = self.addHost('emergency', ip='10.0.0.10')
        # Patient Monitoring Devices
        monitoring = self.addHost('monitoring', ip='10.0.0.20')
        # Medical Imaging Devices
        imaging = self.addHost('imaging', ip='10.0.0.30')
        # Medical Device Host
        med_device = self.addHost('med_device', ip='10.0.0.40')
        # Administrative System
        admin = self.addHost('admin', ip='10.0.0.50')
        # Environmental Sensors
        env_sensor = self.addHost('env_sensor', ip='10.0.0.60')

        # Server to receive all traffic
        server = self.addHost('server', ip='10.0.0.100')
        info('*** Creating links with QoS\n')
        # Links with different bandwidth and latency requirements
        self.addLink(emergency, s1, cls=TCLink, bw=10)  # , delay='2ms', max_queue_size=1000)
        self.addLink(monitoring, s1, cls=TCLink, bw=10)  # , delay='5ms', max_queue_size=1000)
        self.addLink(imaging, s1, cls=TCLink, bw=10)  # , delay='10ms', max_queue_size=1000)
        self.addLink(med_device, s2, cls=TCLink, bw=10)  # , delay='20ms', max_queue_size=1000)
        self.addLink(admin, s2, cls=TCLink, bw=10)  # , delay='50ms', max_queue_size=1000)
        self.addLink(env_sensor, s2, cls=TCLink, bw=10)  # , delay='100ms', max_queue_size=1000)
        self.addLink(server, s3, cls=TCLink, bw=10)  # , delay='1ms', max_queue_size=1000)
        # Inter-switch links
        self.addLink(s1, s2, cls=TCLink, bw=15, delay='1ms')
        self.addLink(s2, s3, cls=TCLink, bw=15, delay='1ms')

def configure_switches(switch):
    info('*** Configuring QoS\n')
    # Configure QoS queues on switches
    # Queue configuration for s1
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")

    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')

    # Clear existing QoS configurations
    for port in range(1, 5):  # Support up to 4 ports per switch
        switch.cmd(f'ovs-vsctl clear Port {switch.name}-eth{port} qos')

    # Configure QoS for each port with three queues
    for port in range(1, 5):
        cmd = f'''ovs-vsctl -- \
                 set Port {switch.name}-eth{port} qos=@newqos -- \
                 --id=@newqos create QoS type=linux-htb \
                 queues:0=@q0 \
                 queues:1=@q1 \
                 queues:2=@q2 -- \
                 --id=@q0 create Queue other-config:min-rate=1000000 \
                                                other-config:max-rate=10000000 -- \
                 --id=@q1 create Queue other-config:min-rate=5000000 \
                                                other-config:max-rate=15000000 -- \
                 --id=@q2 create Queue other-config:min-rate=3000000 \
                                                other-config:max-rate=20000000'''
        switch.cmd(cmd)
"""
Start generating traffic 
"""
def generate_emergency_alerts(host, destination, duration=60):
    """Generate emergency alert traffic"""

    while True:
        # Small packets (100 bytes) with highest priority
        print("^^^^^^^^^^^^generate_emergency_alerts ")
        host.cmd(f'ping -c 1 -s 100 -Q 0x28 {destination} &')
        time.sleep(random.uniform(0.5, 10.0))  # Random intervals

def generate_patient_monitoring(host, destination, duration=60):
    """Generate continuous patient monitoring data"""
    # Use iperf for continuous stream with specific QoS

    host.cmd(f'iperf -c {destination} -t {duration} -u -b 2M -Q 0x20 &')
    # Add some additional monitoring data simulation
    while True:
        # Simulate vital signs data packets
        host.cmd(f'ping -c 1 -s 200 -Q 0x20 {destination}')
        print("%%%%%%%%%%%%%%%%%%%%%%%%generate_patient_monitoring")
        # Add some random vitals data
        time.sleep(random.uniform(0.2, 0.5))  # More frequent updates for patient monitoring


def generate_medical_imaging(host, destination, duration=60):
    """Generate large medical imaging data"""
    # Large data transfer with high bandwidth
    print("****************generate_medical_imaging ")
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
            print(f"  Capturing tcpDump on Interface: {interfaces}")
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


def main():
    setLogLevel('info')  # Enable Mininet logs
    # 1. Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    os.system('pkill -f tcpdump')  # Add this line to clean up any lingering tcpdump processes

    #2. Create Custom Topology
    topo = customTopology()
    # Create and start network
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=Controller,
        link=TCLink,
        autoSetMacs=True
    )

    net.start()
    print("Waiting for network to initialize...")
    sleep(5)
    tcpdump_collector = TCPDumpCollector(net, output_dir='tcpdump_data')

    # Access switches in the network for diplaying interfaces
    for switch in net.switches:
        print(f"Switch: {switch.name}")
        for intf in switch.intfList():
            print(f"  Interface: {intf.name}")


    # Start traffic generators in separate threads
    info('*** Starting traffic generation\n')
    for host in net.hosts:
        print(f"Host: {host.name}")
        for intf in host.intfList():
            print(f"  Interface: {intf.name}")

    threads = []

    e_thread = threading.Thread(target=generate_emergency_alerts,
                                args=(net.get('emergency'), '10.0.0.100'))
    pm_thread = threading.Thread(target=generate_patient_monitoring,
                                 args=(net.get('monitoring'), '10.0.0.100'))
    gmi_thread = threading.Thread(target=generate_medical_imaging,
                                  args=(net.get('imaging'), '10.0.0.100'))

    threads.extend([e_thread, pm_thread, gmi_thread])

    # Start all threads
    for thread in threads:
        thread.daemon = True  # Make threads daemon so they exit when main program exits
        thread.start()

    try:
        # Start tcpdump on all hosts
        for host in net.hosts:
            print(f"Host: {host.name}")
            tcpdump_collector.start_capture(host)
        # Initialize and start network monitor
        #  monitor = NetworkMonitor(net, stats_collector)
        # monitor.start_monitoring()

        # Add custom commands to Mininet CLI
        CLI.do_showstats = lambda self, _: print_network_stats(stats_collector)
        CLI.do_stoptcpdump = lambda self, _: tcpdump_collector.stop_capture()

        print("\nNetwork is ready.")
        print("Available commands:")
        print("  showstats - Show current network statistics")
        print("  stoptcpdump - Stop all tcpdump captures")
        info('*** Running CLI\n')
        CLI(net)


    except Exception as e:
        print(f"Error during network operation: {e}")

    finally:
        # Cleanup
        print("Cleaning up...")
        tcpdump_collector.cleanup()
        # monitor.stop_monitoring()
        info('*** Stopping network\n')
        net.stop()
        os.system('pkill -f tcpdump')  # Final cleanup of any remaining tcpdump processes

        # No need to join threads since they're daemon threads




if __name__ == '__main__':
    main()


