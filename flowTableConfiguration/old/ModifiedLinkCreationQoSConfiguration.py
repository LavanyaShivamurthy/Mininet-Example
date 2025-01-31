from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
from time import sleep

class CustomTCLink(TCLink):
    """Custom TCLink with modified parameters"""
    def __init__(self, *args, **kwargs):
        # Modify the bandwidth parameters before calling parent
        if 'params1' in kwargs and 'bw' in kwargs['params1']:
            # Split the bandwidth into two parts
            bw = kwargs['params1']['bw']
            kwargs['params1']['bw'] = bw/2
            if 'params2' in kwargs:
                kwargs['params2']['bw'] = bw/2
        super(CustomTCLink, self).__init__(*args, **kwargs)

class ModifiedTopoOF13(Topo):
    def build(self):
        # Create hosts and switches
        h1 = self.addHost('h1')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        h2 =self.addHost('h2')      
        # Split the 18Mbps into two 9Mbps links logically
        link_config = dict(
            bw=36,  # Half of 18Mbps
            delay='5ms',
            loss=1,
            use_htb=True,
            max_queue_size=1000
        )
        
        self.addLink(h1, s1, **link_config)
        self.addLink(h2, s1, **link_config)

def configure_qos(node, interface):
    """Configure QoS settings"""
    print(f"Configuring QoS for {interface}")
    
    # Remove existing configuration
    node.cmd(f'tc qdisc del dev {interface} root')
    
    # Create root HTB qdisc
    node.cmd(f'tc qdisc add dev {interface} root handle 1: htb default 11 r2q 1')
    
    # Create parent class
    node.cmd(f'tc class add dev {interface} parent 1: classid 1:1 htb rate 9mbit ceil 9mbit')
    
    # Create child class
    node.cmd(f'tc class add dev {interface} parent 1:1 classid 1:11 htb rate 9mbit ceil 9mbit burst 15k')
    
    # Add netem for delay and loss
    node.cmd(f'tc qdisc add dev {interface} parent 1:11 handle 10: netem delay 5ms loss 1%')

def configure_switch(switch):
    """Configure switch settings"""
    print(f"Configuring {switch.name}")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Configure each port
    for port in range(1, 2):
        port_name = f"{switch.name}-eth{port}"
        
        # Clear existing QoS
        switch.cmd(f'ovs-vsctl clear Port {port_name} qos')
        
        # Set up QoS
        cmd = f'''ovs-vsctl -- \
                set Port {port_name} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=9000000 \
                queues:0=@q0 -- \
                --id=@q0 create Queue other-config:min-rate=1000000 \
                                               other-config:max-rate=9000000'''
        switch.cmd(cmd)
        
        configure_qos(switch, port_name)

def main():
    setLogLevel('info')
    
    # Clean up
    os.system('mn -c')
    os.system('killall controller')
    
    # Create and start network with custom link class
    topo = ModifiedTopoOF13()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=Controller,
        link=CustomTCLink,  # Use our custom link class
        autoSetMacs=True
    )

    net.start()
    print("Waiting for network to initialize...")
    sleep(2)

    # Configure hosts
    for host in net.hosts:
        for intf in host.intfList():
            if intf.name != 'lo':
                configure_qos(host, intf.name)

    # Configure switches
    for switch in net.switches:
        configure_switch(switch)

    print("\nNetwork is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
