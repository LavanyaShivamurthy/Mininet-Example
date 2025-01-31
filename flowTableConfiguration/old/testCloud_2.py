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
        
        # Create switches
        s1 = self.addSwitch('s1', protocols='OpenFlow13')

        # Modified link configuration
        # Using smaller bandwidth values and adjusted parameters
        host_link_config = dict(
            bw=18,
            delay='5ms',
            loss=1,
            use_htb=True,
            max_queue_size=1000
        )
        
        # Add the link
        self.addLink(h1, s1, **host_link_config)
        
def configure_tc(node, interface):
    """Configure traffic control settings directly"""
    print(f"Configuring tc for {interface}")
    
    # Remove existing qdisc
    node.cmd(f'tc qdisc del dev {interface} root')
    
    # Add root HTB qdisc with smaller default quantum
    node.cmd(f'tc qdisc add dev {interface} root handle 1: htb default 1')
    
    # Add main class with adjusted rates
    node.cmd(f'tc class add dev {interface} parent 1: classid 1:1 htb rate 18mbit burst 15k')
    
    # Add netem qdisc for delay and loss
    node.cmd(f'tc qdisc add dev {interface} parent 1:1 handle 10: netem delay 5ms loss 1%')

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS configurations
    for port in range(1, 5):
        port_name = f"{switch.name}-eth{port}"
        switch.cmd(f'ovs-vsctl clear Port {port_name} qos')
    
    # Configure QoS for each port
    for port in range(1, 5):
        port_name = f"{switch.name}-eth{port}"
        
        # Configure tc settings first
        configure_tc(switch, port_name)
        
        # Then set up OVS QoS
        cmd = f'''ovs-vsctl -- \
                set Port {port_name} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=18000000 \
                queues:0=@q0 \
                queues:1=@q1 \
                queues:2=@q2 -- \
                --id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=6000000 -- \
                --id=@q1 create Queue other-config:min-rate=2000000 other-config:max-rate=12000000 -- \
                --id=@q2 create Queue other-config:min-rate=3000000 other-config:max-rate=18000000'''
        switch.cmd(cmd)

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add table-miss flow entry
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'table=0,priority=0,actions=CONTROLLER:65535')
    
    flow_rules = [
        'priority=65535,arp,actions=FLOOD',
        'priority=65535,dl_type=0x88cc,actions=FLOOD',
        'priority=10000,ip,nw_proto=1,actions=set_queue:2,FLOOD',
        'priority=9000,tcp,actions=set_queue:1,FLOOD',
        'priority=8000,udp,actions=set_queue:0,FLOOD',
        'priority=5000,ip,actions=set_queue:0,FLOOD'
    ]
    
    for rule in flow_rules:
        switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, rule)

def configure_host_tc(net):
    """Configure traffic control settings for hosts"""
    for host in net.hosts:
        for intf in host.intfList():
            if intf.name != 'lo':
                configure_tc(host, intf.name)

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

    # Configure tc for hosts first
    configure_host_tc(net)

    # Then configure switches and add flows
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)
    
    dumpNodeConnections(net.hosts)
    print("\nNetwork is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
