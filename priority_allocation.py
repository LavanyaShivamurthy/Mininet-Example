from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch
from mininet.cli import CLI

class CustomTopo(Topo):
    def build(self):
        # Create two hosts and a switch
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        
        # Connect hosts to the switch
        self.addLink(h1, s1)
        self.addLink(h2, s1)

net = Mininet(topo=CustomTopo(), switch=OVSSwitch)
net.start()

# Set up traffic control on h1 and assign high priority to ICMP traffic
h1 = net.get('h1')
h1.cmd('tc qdisc add dev h1-eth0 root handle 1: htb')
h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:1 htb rate 1mbit')
h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:2 htb rate 500kbit')
h1.cmd('tc filter add dev h1-eth0 protocol ip parent 1: prio 1 u32 match ip protocol 1 0xff flowid 1:1')  # ICMP (ping)

CLI(net)
net.stop()

