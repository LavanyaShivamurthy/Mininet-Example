from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
from time import sleep

class SplitBandwidthTopo(Topo):
    def build(self):
        # Create hosts and switches
        h1 = self.addHost('h1')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        h2 = self.addHost('h2')
        
        # Link configuration with 18Mbps total bandwidth
        link_config = dict(
            bw=18,
            delay='5ms',
            loss=1,
            use_htb=True,
            max_queue_size=1000
        )
        
        self.addLink(h1, s1, **link_config)
        self.addLink(h2, s1,**link_config)

def configure_split_bandwidth(node, interface):
    """Configure QoS with split bandwidth classes"""
    print(f"Configuring split bandwidth QoS for {interface}")
    
    # Remove existing configuration
    node.cmd(f'tc qdisc del dev {interface} root')
    
    # Create root HTB qdisc
    node.cmd(f'tc qdisc add dev {interface} root handle 1: htb default 12')
    
    # Create parent class for total bandwidth
    node.cmd(f'tc class add dev {interface} parent 1: classid 1:1 htb rate 18mbit ceil 18mbit')
    
    # Split into two child classes, each under 15Mbps
    node.cmd(f'tc class add dev {interface} parent 1:1 classid 1:11 htb rate 9mbit ceil 9mbit burst 15k')
    node.cmd(f'tc class add dev {interface} parent 1:1 classid 1:12 htb rate 9mbit ceil 9mbit burst 15k')
    
    # Add netem for delay and loss to each class
    node.cmd(f'tc qdisc add dev {interface} parent 1:11 handle 10: netem delay 5ms loss 1%')
    node.cmd(f'tc qdisc add dev {interface} parent 1:12 handle 20: netem delay 5ms loss 1%')
    
    # Add filters to distribute traffic
    node.cmd(f'tc filter add dev {interface} protocol ip parent 1: prio 1 u32 match ip sport 0 0xffff flowid 1:11')
    node.cmd(f'tc filter add dev {interface} protocol ip parent 1: prio 2 u32 match ip dport 0 0xffff flowid 1:12')

def configure_switch(switch):
    """Configure switch with split bandwidth QoS"""
    print(f"Configuring {switch.name}")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Configure each port
    for port in range(1, 2):  # Only configure first port
        port_name = f"{switch.name}-eth{port}"
        
        # Clear existing QoS
        switch.cmd(f'ovs-vsctl clear Port {port_name} qos')
        
        # Set up QoS with split queues
        cmd = f'''ovs-vsctl -- \
                set Port {port_name} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=18000000 \
                queues:0=@q0 \
                queues:1=@q1 -- \
                --id=@q0 create Queue other-config:min-rate=10000000 other-config:max-rate=10000000 -- \
                --id=@q1 create Queue other-config:min-rate=8000000 other-config:max-rate=8000000'''
        switch.cmd(cmd)
        
        # Configure tc settings
        configure_split_bandwidth(switch, port_name)

def add_flows(switch):
    """Add flow rules for split bandwidth"""
    print(f"Adding flows to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add basic flows
    flows = [
        'table=0,priority=0,actions=CONTROLLER:65535',
        'priority=100,tcp,actions=set_queue:0,NORMAL',
        'priority=100,udp,actions=set_queue:1,NORMAL'
    ]
    
    for flow in flows:
        switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, flow)

def main():
    setLogLevel('info')
    
    # Clean up
    os.system('mn -c')
    os.system('killall controller')
    
    # Create and start network
    topo = SplitBandwidthTopo()
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

    # Configure hosts
    for host in net.hosts:
        for intf in host.intfList():
            if intf.name != 'lo':
                configure_split_bandwidth(host, intf.name)

    # Configure switches
    for switch in net.switches:
        configure_switch(switch)
        add_flows(switch)

    print("\nNetwork is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
