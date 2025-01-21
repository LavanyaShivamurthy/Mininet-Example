#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
from time import sleep

def createIoTNetwork():
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8',
                  controller=Controller)  # Using default controller

    # Add controller
    info('*** Adding controller\n')
    c0 = net.addController('c0')  # Default controller

    # Add switches
    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)

    # Add IoT devices (hosts)
    info('*** Adding IoT devices (hosts)\n')
    h1 = net.addHost('h1', cls=Host, ip='10.0.0.1')
    h2 = net.addHost('h2', cls=Host, ip='10.0.0.2')
    h3 = net.addHost('h3', cls=Host, ip='10.0.0.3')
    h4 = net.addHost('h4', cls=Host, ip='10.0.0.4')

    # Add links
    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s3)
    net.addLink(s1, s2)
    net.addLink(s2, s3)

    # Start network
    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    # Configure flow tables
    info('*** Configuring flow tables\n')
    
    # Example flow rules using ovs-ofctl
    # Allow ARP
    s1.cmd('ovs-ofctl add-flow s1 priority=1,arp,actions=flood')
    s2.cmd('ovs-ofctl add-flow s2 priority=1,arp,actions=flood')
    s3.cmd('ovs-ofctl add-flow s3 priority=1,arp,actions=flood')
    
    # Direct traffic between h1 and h3
    s1.cmd('ovs-ofctl add-flow s1 priority=2,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=output:3')
    s2.cmd('ovs-ofctl add-flow s2 priority=2,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=output:1')
    
    # Direct traffic between h2 and h4
    s1.cmd('ovs-ofctl add-flow s1 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=output:3')
    s2.cmd('ovs-ofctl add-flow s2 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=output:3')
    s3.cmd('ovs-ofctl add-flow s3 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=output:1')

    info('*** Running CLI\n')
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    createIoTNetwork()
