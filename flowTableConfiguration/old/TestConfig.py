from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI

class QoSNetwork(Topo):
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

        # Add links with bandwidth constraints
        # Parameters: bw (Mbps), delay (ms), max_queue_size
        self.addLink(h1, s1, bw=10, delay='5ms', max_queue_size=1000)
        self.addLink(h2, s1, bw=10, delay='5ms', max_queue_size=1000)
        self.addLink(h3, s1, bw=10, delay='5ms', max_queue_size=1000)
        self.addLink(s1, s2, bw=50, delay='10ms', max_queue_size=1000)
        self.addLink(s2, h4, bw=10, delay='5ms', max_queue_size=1000)
        self.addLink(s2, h5, bw=10, delay='5ms', max_queue_size=1000)

def configure_qos(net):
    # Get hosts
    h1, h2, h3, h4, h5 = net.get('h1', 'h2', 'h3', 'h4', 'h5')
    
    # Configure HTB qdisc on h1's interface
    h1.cmd('tc qdisc del dev h1-eth0 root')
    h1.cmd('tc qdisc add dev h1-eth0 root handle 1: htb default 20')
    
    # Add classes for different types of traffic
    # Class 1:10 - High priority (e.g., VoIP)
    h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:10 htb rate 5Mbit ceil 10Mbit')
    # Class 1:20 - Medium priority (e.g., HTTP)
    h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:20 htb rate 3Mbit ceil 8Mbit')
    # Class 1:30 - Low priority (e.g., FTP)
    h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:30 htb rate 2Mbit ceil 5Mbit')
    
    # Add filters to classify traffic
    h1.cmd('tc filter add dev h1-eth0 protocol ip parent 1: prio 1 u32 match ip dport 5201 0xffff flowid 1:10')  # VoIP
    h1.cmd('tc filter add dev h1-eth0 protocol ip parent 1: prio 2 u32 match ip dport 80 0xffff flowid 1:20')    # HTTP
    h1.cmd('tc filter add dev h1-eth0 protocol ip parent 1: prio 3 u32 match ip dport 21 0xffff flowid 1:30')    # FTP

def run_network():
    topo = QoSNetwork()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    
    # Configure QoS
    configure_qos(net)
    
    # Run tests
    print("Testing network connectivity")
    net.pingAll()
    
    # Start CLI
    CLI(net)
    
    # Cleanup
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_network()
