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

h1, h2, s1 = net.get('h1', 'h2', 's1')
#Apply traffic control to h1’s interface (h1-eth0) to prioritize ICMP traffic
h1.cmd('tc qdisc add dev h1-eth0 root handle 1: htb')
# High priority for ICMP traffic (1mbit rate)
h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:1 htb rate 1mbit')
# Lower priority for other traffic (0.5mbit rate)i
#h1 = net.get('h1')
h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:2 htb rate 0.5mbit')
h1.cmd('tc filter add dev h1-eth0 protocol ip parent 1: prio 1 u32 match ip protocol 1 0xff flowid 1:1')
#h1.cmd('tcpdump -i h1-eth0 -w /tmp/capture.pcap &')
h1.cmd('ping -c 10 10.0.0.2 &')
h1.cmd('iperf -c 10.0.0.2 -t 10 -i 1 &')

CLI(net)
net.stop()

