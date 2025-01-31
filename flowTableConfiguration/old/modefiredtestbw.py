"""
This Program is to set the bandwidth above 10Mbs
Topolgy
     ____________________h1
     |
s1 _  |
    |
    |_________________h2



    sudo python1 testbw.py
    mininet> xterm h1 h2
   at h1 iperf -s
   at h1 ifconfig
    at    iperf -c 10.0.0.1 <h2>
    mininet> h1 tc qdisc change dev h1-eth0 root tbf rate 30mbit burst 100kb limit 200kb
    mininet> h1 tc qdisc show dev h1-eth0
"""



from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

class SimpleTBFTopo(Topo):
    def build(self):
        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Add switch
        s1 = self.addSwitch('s1')

        # Add links
        self.addLink(h1, s1)
        self.addLink(s1, h2)

def configure_tbf(net):
    h1 = net.get('h1')
    h1.cmd('tc qdisc del dev h1-eth0 root')
    h1.cmd('tc qdisc add dev h1-eth0 root tbf rate 20mbit burst 100kb limit 200kb')
    print("\nQdisc configuration on h1-eth0:")
    print(h1.cmd('tc qdisc show dev h1-eth0'))

def run_network():
    topo = SimpleTBFTopo()
    # Remove CPULimitedHost here
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    
    configure_tbf(net)
    
    print("\nTesting network connectivity")
    net.pingAll()
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_network()
