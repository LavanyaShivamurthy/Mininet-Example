from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink  # To configure bandwidth
from mininet.log import setLogLevel

def customTopology():
    # Set up the network
    net = Mininet(controller=Controller, link=TCLink)
    
    # Add a default controller
    net.addController('c0')
    
    # Add switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    
    # Add hosts
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    
    # Add links with specified bandwidth
    net.addLink(h1, s1, bw=10)  # 10 Mbps between h1 and s1
    net.addLink(h2, s2, bw=10)  # 10 Mbps between h2 and s2
    net.addLink(s1, s2, bw=100)  # 100 Mbps between s1 and s2
    
    # Build and start the network
    net.build()
    net.start()
    
    print("Testing network connectivity...")
    net.pingAll()  # Test connectivity between all nodes
    
    # Stop the network after testing
    net.stop()

if __name__ == '__main__':
    # Set Mininet log level to info
    setLogLevel('info')
    
    # Run the custom topology
    customTopology()

