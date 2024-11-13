from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
from time import sleep

class ExpandedQoSTopoOF13(Topo):
    def build(self):
        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')

        # Create switches
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', protocols='OpenFlow13')
        
        # Add host links with QoS parameters
        # Edge links (hosts to switches)
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
        self.addLink(s1, s4, cls=TCLink, bw=20, delay='2ms', loss=0)  # Alternative path

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS configurations
    for port in range(1, 5):  # Support up to 4 ports per switch
        switch.cmd(f'ovs-vsctl clear Port {switch.name}-eth{port} qos')
    
    # Configure QoS for each port
    for port in range(1, 5):
        switch.cmd(f'ovs-vsctl -- set Port {switch.name}-eth{port} qos=@newqos -- \
                  --id=@newqos create QoS type=linux-htb \
                  queues=0=@q0,1=@q1,2=@q2 -- \
                  --id=@q0 create Queue other-config:max-rate=1000000 -- \
                  --id=@q1 create Queue other-config:min-rate=5000000 -- \
                  --id=@q2 create Queue other-config:min-rate=3000000')

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add table-miss flow entry
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'table=0,priority=0,actions=CONTROLLER:65535')
    
    # Add MAC learning flows
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch,
              'table=0,priority=1,arp,actions=FLOOD')
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch,
              'table=0,priority=1,icmp,actions=FLOOD')
    
    # QoS rules for different traffic types with explicit forwarding
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch,
              'priority=100,ip,nw_proto=1,actions=set_queue:2,FLOOD')  # ICMP
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch,
              'priority=90,tcp,actions=set_queue:1,FLOOD')  # TCP
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch,
              'priority=80,udp,actions=set_queue:0,FLOOD')  # UDP
    
    print("\nVerifying flows:")
    print(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows', switch))

def setup_network():
    """Create and configure the network"""
    topo = ExpandedQoSTopoOF13()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=Controller,
        link=TCLink,
        autoSetMacs=True
    )
    
    net.start()
    
    # Wait for network to initialize
    print("Waiting for network to initialize...")
    sleep(2)
    
    # Configure switches
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)
    
    # Ensure all hosts can see each other by updating ARP tables
    print("\nUpdating ARP tables...")
    for h1 in net.hosts:
        for h2 in net.hosts:
            if h1 != h2:
                h1.cmd(f'arp -s {h2.IP()} {h2.MAC()}')
    
    return net

def test_expanded_network(net):
    "Test connectivity and QoS in the expanded network"
    print("\nDumping host connections")
    dumpNodeConnections(net.hosts)
    
    # Get all hosts
    h1, h2, h3, h4, h5, h6 = net.get('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
    
    # Print network information
    print("\nHost IP and MAC addresses:")
    for host in net.hosts:
        print(f"{host.name}: IP={host.IP()}, MAC={host.MAC()}")
    
    print("\nTesting connectivity across the network:")
    
    # Test ping between various hosts with increasing verbosity
    print("\nTesting ping from h1 to h6:")
    print(h1.cmd('ping -c 3', h6.IP()))
    
    print("\nTesting ping from h2 to h4:")
    print(h2.cmd('ping -c 3', h4.IP()))
    
    print("\nTesting ping from h3 to h5:")
    print(h3.cmd('ping -c 3', h5.IP()))
    
    # Test bandwidth between hosts
    print("\nTesting TCP bandwidth between multiple host pairs")
    
    # Start iperf servers
    h4.cmd('iperf -s &')
    h6.cmd('iperf -s &')
    sleep(1)
    
    print("\nTesting TCP bandwidth from h1 to h4:")
    print(h1.cmd('iperf -c', h4.IP(), '-t 5 -i 1'))
    
    print("\nTesting TCP bandwidth from h2 to h6:")
    print(h2.cmd('iperf -c', h6.IP(), '-t 5 -i 1'))
    
    # Clean up iperf servers
    h4.cmd('kill %iperf')
    h6.cmd('kill %iperf')

def main():
    setLogLevel('info')
    
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    
    print("Starting expanded QoS network with OpenFlow 1.3")
    net = setup_network()
    
    print("\nNetwork is ready")
    test_expanded_network(net)
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
