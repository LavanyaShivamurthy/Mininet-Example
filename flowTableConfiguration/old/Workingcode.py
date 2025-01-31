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

class TopoOF13(Topo):
    def build(self):
        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        
        # Create switches
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')

        # Host links - 10Mbps
        # Calculate r2q: For 10Mbps, use r2q=1 to keep quantum small
        host_link_config = dict(
            bw=10,
            delay='5ms',
            loss=1,
            use_htb=True,
            r2q=1,
            max_queue_size=10000,
            burst=1500  # MTU size
        )
        
        self.addLink(h1, s1, **host_link_config)
        self.addLink(h2, s1, **host_link_config)
        self.addLink(h3, s2, **host_link_config)

        # Switch interconnection - 100Mbps
        # For 100Mbps, adjust r2q to 1 but increase burst size
        switch_link_config = dict(
            bw=10,
            delay='2ms',
            loss=0,
            use_htb=True,
            r2q=5,
            max_queue_size=1000,
            burst=15000  # 10x MTU size for higher bandwidth
        )
        
        self.addLink(s1, s2, **switch_link_config)

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS configurations
    for port in range(1, 5):
        switch.cmd(f'ovs-vsctl clear Port {switch.name}-eth{port} qos')
        # Remove existing qdisc
        switch.cmd(f'tc qdisc del dev {switch.name}-eth{port} root')
    
    # Configure QoS with refined parameters
    for port in range(1, 5):
        # First, set up basic HTB qdisc
        switch.cmd(f'tc qdisc add dev {switch.name}-eth{port} root handle 1: htb default 10')
        
        # Add root class with max rate
        switch.cmd(f'tc class add dev {switch.name}-eth{port} parent 1: classid 1:1 htb rate 100Mbit burst 15k')
        
        # Add subclasses for different priorities
        switch.cmd(f'tc class add dev {switch.name}-eth{port} parent 1:1 classid 1:10 htb rate 10Mbit ceil 100Mbit burst 15k')
        switch.cmd(f'tc class add dev {switch.name}-eth{port} parent 1:1 classid 1:20 htb rate 20Mbit ceil 100Mbit burst 15k')
        switch.cmd(f'tc class add dev {switch.name}-eth{port} parent 1:1 classid 1:30 htb rate 30Mbit ceil 100Mbit burst 15k')
        
        # Now set up OVS QoS
        cmd = f'''ovs-vsctl -- \
                set Port {switch.name}-eth{port} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=100000000 \
                other-config:burst=15000 \
                queues:0=@q0 \
                queues:1=@q1 \
                queues:2=@q2 -- \
                --id=@q0 create Queue other-config:min-rate=10000000 \
                                               other-config:max-rate=100000000 \
                                               other-config:burst=15000 -- \
                --id=@q1 create Queue other-config:min-rate=20000000 \
                                               other-config:max-rate=100000000 \
                                               other-config:burst=15000 -- \
                --id=@q2 create Queue other-config:min-rate=30000000 \
                                               other-config:max-rate=100000000 \
                                               other-config:burst=15000'''
        switch.cmd(cmd)

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add flow rules
    flow_rules = [
        'table=0,priority=0,actions=CONTROLLER:65535',
        'priority=65535,arp,actions=FLOOD',
        'priority=65535,dl_type=0x88cc,actions=FLOOD',
        'priority=10000,ip,nw_proto=1,actions=set_queue:2,FLOOD',
        'priority=9000,tcp,actions=set_queue:1,FLOOD',
        'priority=8000,udp,actions=set_queue:0,FLOOD',
        'priority=5000,ip,actions=set_queue:0,FLOOD'
    ]
    
    for rule in flow_rules:
        switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, rule)

def main():
    setLogLevel('info')
    
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    os.system('pkill -f tcpdump')
    
    print("Starting QoS network with statistics monitoring")
    
    topo = TopoOF13()
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

    # Configure switches
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)

    print("\nNetwork is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
