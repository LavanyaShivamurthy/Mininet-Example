from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI

class ExpandedTopo(Topo):
    def build(self):
        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')

        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Add links with bandwidth constraints and r2q parameter
        # Switch to Switch links
        self.addLink(s1, s2, bw=10, delay='5ms', use_htb=True, r2q=1000)
        self.addLink(s2, s3, bw=10, delay='5ms', use_htb=True, r2q=1000)

        # Host to Switch links
        self.addLink(h1, s1, bw=10, delay='2ms', use_htb=True, r2q=100)
        self.addLink(h2, s1, bw=10, delay='2ms', use_htb=True, r2q=100)
        self.addLink(h3, s2, bw=10, delay='2ms', use_htb=True, r2q=100)
        self.addLink(h4, s3, bw=10, delay='2ms', use_htb=True, r2q=100)
        self.addLink(h5, s3, bw=10, delay='2ms', use_htb=True, r2q=100)







def configure_qos(net):
    # Configure QoS for each host
    for host in net.hosts:
        # Configure TBF on each host's interface
        host.cmd(f'tc qdisc del dev {host.name}-eth0 root')
        host.cmd(f'tc qdisc add dev {host.name}-eth0 root tbf rate 10mbit burst 100kb limit 200kb')

def run_network():
    # Create topology
    topo = ExpandedTopo()
    
    # Create network with remote controller
    controller = RemoteController('c0', ip='127.0.0.1', port=6653)
    net = Mininet(topo=topo, link=TCLink, controller=controller)
    
    # Start network
    net.start()
    
    # Configure QoS
    configure_qos(net)
    
    # Print connection information
    print("\nDumping host connections")
    dumpNodeConnections(net.hosts)
    
    # Test network connectivity
    print("\nTesting network connectivity")
    net.pingAll()
    
    print("\nNetwork is ready!")
    print("Topology: 3 switches, 5 hosts, with OpenFlow controller")
    print("All host links: 10 Mbps")
    print("All switch-to-switch links: 100 Mbps")
    print("\nTo test bandwidth between hosts, use:")
    print("1. Start iperf server on destination: 'iperf -s'")
    print("2. Start iperf client on source: 'iperf -c <destination IP>'")
    
    # Start CLI
    CLI(net)
    
    # Cleanup
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_network()
