from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.log import setLogLevel
import os

def set_custom_quantum(interface, quantum):
    # Use the tc command to adjust quantum
    os.system(f"tc qdisc change dev {interface} root handle 1: htb default 1 quantum {quantum}")

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
    
    # Add links with bandwidth, delay, and loss
    net.addLink(h1, s1, bw=18, delay='5ms', loss=1, use_htb=True)  # 18 Mbps with delay and loss
    net.addLink(h2, s2, bw=18, delay='5ms', loss=1, use_htb=True)  # 18 Mbps with delay and loss
    net.addLink(s1, s2, bw=18, delay='5ms', loss=1, use_htb=True)  # 18 Mbps with delay and loss
    
    # Build and start the network
    net.build()
    net.start()
    
    # Adjust quantum manually for all interfaces
    set_custom_quantum('s1-eth1', 3000)
    set_custom_quantum('s2-eth1', 3000)
    set_custom_quantum('s1-eth2', 3000)
    
    print("Testing network connectivity...")
    net.pingAll()  # Test connectivity between all nodes
    
    # Stop the network after testing
    net.stop()

if __name__ == '__main__':
    # Set Mininet log level to info
    setLogLevel('info')
    
    # Run the custom topology
    customTopology()

