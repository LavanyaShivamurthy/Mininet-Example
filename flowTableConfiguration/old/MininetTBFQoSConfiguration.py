from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
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
    # Get host h1
    h1 = net.get('h1')
    
    # Configure TBF on h1's interface
    # Rate: 20Mbit
    # Burst: 100kb
    # Limit: 200kb
    h1.cmd('tc qdisc del dev h1-eth0 root')
    h1.cmd('tc qdisc add dev h1-eth0 root tbf rate 20mbit burst 100kb limit 200kb')
    
    # Verify the configuration
    print("\nQdisc configuration on h1-eth0:")
    print(h1.cmd('tc qdisc show dev h1-eth0'))

def run_network():
    # Create network
    topo = SimpleTBFTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    
    # Configure TBF
    configure_tbf(net)
    
    # Test connectivity
    print("\nTesting network connectivity")
    net.pingAll()
    
    print("\nNetwork is ready for testing!")
    print("To test bandwidth limitation, use iperf3 in the CLI:")
    print("1. On h2: 'iperf3 -s'")
    print("2. On h1: 'iperf3 -c h2'")
    
    # Start CLI
    CLI(net)
    
    # Cleanup
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_network()
