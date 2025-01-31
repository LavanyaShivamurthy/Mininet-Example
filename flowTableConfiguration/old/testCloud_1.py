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

        # Simplified link configuration without r2q
        host_link_config = dict(
            bw=18,
            delay='5ms',
            loss=1,
            use_htb=True,
            max_queue_size=1000
        )
        
        self.addLink(h1, s1, **host_link_config)

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS and tc configurations
    for port in range(1, 5):
        port_name = f"{switch.name}-eth{port}"
        switch.cmd(f'ovs-vsctl clear Port {port_name} qos')
        switch.cmd(f'tc qdisc del dev {port_name} root')
    
    # Configure QoS for each port using tc directly
    for port in range(1, 5):
        port_name = f"{switch.name}-eth{port}"
        
        # Create root HTB qdisc with smaller default quantum
        switch.cmd(f'tc qdisc add dev {port_name} root handle 1: htb default 10 r2q 1')
        
        # Create main class with rate limit
        switch.cmd(f'tc class add dev {port_name} parent 1: classid 1:1 htb rate 100mbit burst 15k')
        
        # Create subclasses for different traffic types
        switch.cmd(f'tc class add dev {port_name} parent 1:1 classid 1:10 htb rate 10mbit ceil 10mbit burst 15k quantum 1500')
        switch.cmd(f'tc class add dev {port_name} parent 1:1 classid 1:20 htb rate 50mbit ceil 50mbit burst 15k quantum 1500')
        switch.cmd(f'tc class add dev {port_name} parent 1:1 classid 1:30 htb rate 100mbit ceil 100mbit burst 15k quantum 1500')
        
        # Add FIFO queuing discipline to leaf classes
        switch.cmd(f'tc qdisc add dev {port_name} parent 1:10 handle 10: pfifo limit 1000')
        switch.cmd(f'tc qdisc add dev {port_name} parent 1:20 handle 20: pfifo limit 1000')
        switch.cmd(f'tc qdisc add dev {port_name} parent 1:30 handle 30: pfifo limit 1000')
        
        # Create OVS QoS entries to map to tc classes
        cmd = f'''ovs-vsctl -- \
                set Port {port_name} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=100000000 \
                queues:0=@q0 \
                queues:1=@q1 \
                queues:2=@q2 -- \
                --id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=10000000 -- \
                --id=@q1 create Queue other-config:min-rate=5000000 other-config:max-rate=50000000 -- \
                --id=@q2 create Queue other-config:min-rate=10000000 other-config:max-rate=100000000'''
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

    # Configure switches and add flows
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)
    
    dumpNodeConnections(net.hosts)
    print("\nNetwork is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
