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
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')

        # Create switches with OpenFlow 1.3
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', protocols='OpenFlow13')

        # Host links with correct parameters
        linkopts = dict(bw=10, delay='5ms', loss=1, max_queue_size=1000)
        self.addLink(h1, s1, cls=TCLink, **linkopts)
        self.addLink(h2, s1, cls=TCLink, **linkopts)
        self.addLink(h3, s2, cls=TCLink, **linkopts)
        self.addLink(h4, s3, cls=TCLink, **linkopts)
        self.addLink(h5, s4, cls=TCLink, **linkopts)
        self.addLink(h6, s4, cls=TCLink, **linkopts)

        # Switch interconnections with higher bandwidth
        switchlinkopts = dict(bw=200, delay='2ms', loss=0, max_queue_size=1000)
        self.addLink(s1, s2, cls=TCLink, **switchlinkopts)
        self.addLink(s2, s3, cls=TCLink, **switchlinkopts)
        self.addLink(s3, s4, cls=TCLink, **switchlinkopts)
        self.addLink(s1, s4, cls=TCLink, **switchlinkopts)

def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS configurations
    for port in range(1, 5):
        switch.cmd(f'ovs-vsctl clear Port {switch.name}-eth{port} qos')
    
    # Configure QoS with proper HTB settings
    for port in range(1, 5):
        cmd = f'''ovs-vsctl -- \
                set Port {switch.name}-eth{port} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                other-config:max-rate=200000000 \
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

def configure_htb_qdisc(switch):
    """Configure HTB qdisc on switch interfaces"""
    interfaces = switch.intfList()
    
    for intf in interfaces:
        if not intf.name.startswith('lo'):
            # Remove existing qdisc
            switch.cmd(f"tc qdisc del dev {intf.name} root")
            # Add HTB qdisc
            switch.cmd(f"tc qdisc add dev {intf.name} root handle 1: htb default 10")
            # Add root class
            switch.cmd(f"tc class add dev {intf.name} parent 1: classid 1:1 htb rate 200Mbit burst 15k")
            # Add subclasses for different traffic types
            switch.cmd(f"tc class add dev {intf.name} parent 1:1 classid 1:10 htb rate 10Mbit ceil 200Mbit burst 15k")
            switch.cmd(f"tc class add dev {intf.name} parent 1:1 classid 1:20 htb rate 50Mbit ceil 200Mbit burst 15k")
            switch.cmd(f"tc class add dev {intf.name} parent 1:1 classid 1:30 htb rate 100Mbit ceil 200Mbit burst 15k")

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
        configure_htb_qdisc(switch)

    print("Network is ready")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
