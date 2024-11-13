from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
from time import sleep

class QoSTopoOF13(Topo):
    def build(self):
        # Create hosts and switch
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        
        # Add links with QoS parameters
        self.addLink(h1, s1, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h2, s1, cls=TCLink, bw=10, delay='5ms', loss=1)

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Configure QoS
    switch.cmd('ovs-vsctl clear Port %s-eth1 qos' % switch.name)
    switch.cmd('ovs-vsctl clear Port %s-eth2 qos' % switch.name)
    
    switch.cmd('ovs-vsctl -- set Port %s-eth1 qos=@newqos -- \
              --id=@newqos create QoS type=linux-htb \
              queues=0=@q0,1=@q1,2=@q2 -- \
              --id=@q0 create Queue other-config:max-rate=1000000 -- \
              --id=@q1 create Queue other-config:min-rate=5000000 -- \
              --id=@q2 create Queue other-config:min-rate=3000000' % switch.name)
    
    switch.cmd('ovs-vsctl -- set Port %s-eth2 qos=@newqos -- \
              --id=@newqos create QoS type=linux-htb \
              queues=0=@q0,1=@q1,2=@q2 -- \
              --id=@q0 create Queue other-config:max-rate=1000000 -- \
              --id=@q1 create Queue other-config:min-rate=5000000 -- \
              --id=@q2 create Queue other-config:min-rate=3000000' % switch.name)

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add basic forwarding rules for all traffic
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 'priority=0,actions=NORMAL')
    
    # Add specific rules for different traffic types
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'priority=100,ip,nw_proto=1,actions=set_queue:2,NORMAL')  # ICMP
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'priority=90,tcp,actions=set_queue:1,NORMAL')  # TCP
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'priority=80,udp,actions=set_queue:0,NORMAL')  # UDP
    
    print("\nVerifying flows:")
    print(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows', switch))

def setup_network():
    "Create network and configure OpenFlow rules"
    topo = QoSTopoOF13()
    
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
    
    return net

def test_network(net):
    "Test network connectivity and QoS"
    print("\nDumping host connections")
    dumpNodeConnections(net.hosts)
    
    h1, h2 = net.get('h1', 'h2')
    
    # Verify interface configuration
    print("\nInterface configuration for h1:")
    print(h1.cmd('ifconfig'))
    print("\nInterface configuration for h2:")
    print(h2.cmd('ifconfig'))
    
    # Verify routing
    print("\nRouting table for h1:")
    print(h1.cmd('route -n'))
    print("\nRouting table for h2:")
    print(h2.cmd('route -n'))
    
    print("\nTesting basic connectivity")
    # Test ping with verbose output
    print(h1.cmd('ping -c 3 -v', h2.IP()))
    
    # Test iperf
    print("\nStarting iperf server on h2")
    h2.cmd('iperf -s &')
    sleep(1)
    
    print("\nTesting TCP bandwidth")
    print(h1.cmd('iperf -c', h2.IP(), '-t 5 -i 1'))
    
    h2.cmd('kill %iperf')

def main():
    setLogLevel('info')
    
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    
    print("Starting QoS network with OpenFlow 1.3")
    net = setup_network()
    
    print("\nNetwork is ready")
    test_network(net)
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
