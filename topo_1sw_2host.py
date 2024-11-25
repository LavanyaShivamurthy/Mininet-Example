""" This is minnet Program to create topology with : Controller --1
                                                     switch --4
                                                     host -- 6
    
"""
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
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

# ... (Previous NetworkStats and NetworkMonitor classes remain the same) ...

class ExpandedQoSTopoOF13(Topo):
    def build(self):
        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')

        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', protocols='OpenFlow13')
        
        # Add host links with QoS parameters
        self.addLink(h1, s1, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h2, s1, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h3, s2, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h4, s3, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h5, s4, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h6, s4, cls=TCLink, bw=10, delay='5ms', loss=1)
        
        # Switch interconnections with higher bandwidth
        self.addLink(s1, s2, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s2, s3, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s3, s4, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s1, s4, cls=TCLink, bw=20, delay='2ms', loss=0)

def configure_switch_of13(switch):
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

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add table-miss flow entry
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'table=0,priority=0,actions=CONTROLLER:65535')
    
    # Add flow rules for different traffic types
    flow_rules = [
        # ARP and LLDP flooding
        'priority=65535,arp,actions=FLOOD',
        'priority=65535,dl_type=0x88cc,actions=FLOOD',
        
        # ICMP traffic (high priority)
        'priority=10000,ip,nw_proto=1,actions=set_queue:2,FLOOD',
        
        # TCP traffic (medium priority)
        'priority=9000,tcp,actions=set_queue:1,FLOOD',
        
        # UDP traffic (low priority)
        'priority=8000,udp,actions=set_queue:0,FLOOD',
        
        # Default rule for remaining IP traffic
        'priority=5000,ip,actions=set_queue:0,FLOOD'
    ]
    
    # Add each rule
    for rule in flow_rules:
        switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, rule)
    
    # Verify flows
    print(f"\nVerifying flows on {switch.name}:")
    print(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows', switch))

def test_network(net):
    """Test network connectivity and QoS"""
    print("\nTesting network connectivity:")
    
    # Get hosts
    h1, h2, h3, h4, h5, h6 = net.get('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
    
    # Test ping between various hosts
    print("\nTesting ping between hosts:")
    pairs = [(h1, h4), (h2, h5), (h3, h6)]
    for src, dst in pairs:
        print(f"\nPing from {src.name} to {dst.name}:")
        print(src.cmd(f'ping -c 3 {dst.IP()}'))
    
    # Test bandwidth between hosts using iperf
    print("\nTesting bandwidth between hosts:")
    for src, dst in pairs:
        print(f"\nBandwidth test from {src.name} to {dst.name}:")
        dst.cmd('iperf -s &')
        sleep(1)
        print(src.cmd(f'iperf -c {dst.IP()} -t 5'))
        dst.cmd('kill %iperf')

def main():
    setLogLevel('info')
    
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    
    print("Starting QoS network with statistics monitoring")
    
    # Initialize network and statistics collector
    topo = ExpandedQoSTopoOF13()
   # stats_collector = NetworkStats()
    
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
    sleep(2)
    
    # Configure switches and add flows
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)
    
    # Initialize and start network monitor
   # monitor = NetworkMonitor(net, stats_collector)
   # monitor.start_monitoring()
    
    # Test network connectivity
    test_network(net)
    
    # Create a background thread to periodically print statistics
    ''' def print_stats_periodically():
        while True:
            print_network_stats(stats_collector)
            sleep(10)
    
    stats_thread = threading.Thread(target=print_stats_periodically)
    stats_thread.daemon = True
    stats_thread.start()'''
    
    # Add custom command to Mininet CLI
   # CLI.do_showstats = lambda self, _: print_network_stats(stats_collector)
    
    print("\nNetwork is ready. Type 'showstats' to see current statistics.")
    CLI(net)
    
    # Cleanup
    monitor.stop_monitoring()
    net.stop()

if __name__ == '__main__':
    main()
