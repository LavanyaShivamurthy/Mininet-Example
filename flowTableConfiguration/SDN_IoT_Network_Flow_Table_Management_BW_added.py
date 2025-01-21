#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from subprocess import call
from time import sleep

def createIoTNetwork():
    # Create network with TC link support
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8',
                  controller=Controller,
                  link=TCLink)  # Enable TCLink for bandwidth control

    # Add controller
    info('*** Adding controller\n')
    c0 = net.addController('c0')

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

    # Add links with bandwidth constraints
    info('*** Creating links with bandwidth limits\n')
    # Host to switch links (10 Mbps)
    net.addLink(h1, s1, cls=TCLink, bw=10)  # 10 Mbps
    net.addLink(h2, s1, cls=TCLink, bw=10)
    net.addLink(h3, s2, cls=TCLink, bw=10)
    net.addLink(h4, s3, cls=TCLink, bw=10)
    
    # Switch to switch links (20 Mbps)
    net.addLink(s1, s2, cls=TCLink, bw=15)  # 20 Mbps backbone
    net.addLink(s2, s3, cls=TCLink, bw=15)

    # Start network
    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    # Configure QoS and Flow Rules
    info('*** Configuring QoS and Flow Rules\n')
    
    # Configure QoS on switch ports
    # Set up queues on s1
    s1.cmd('ovs-vsctl -- set Port s1-eth1 qos=@newqos -- \
            --id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 \
            queues=0=@q0,1=@q1,2=@q2 -- \
            --id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=10000000 -- \
            --id=@q1 create Queue other-config:min-rate=5000000 other-config:max-rate=8000000 -- \
            --id=@q2 create Queue other-config:min-rate=2000000 other-config:max-rate=5000000')

    # Basic flow rules with queue assignments
    # Allow ARP
    s1.cmd('ovs-ofctl add-flow s1 priority=1,arp,actions=FLOOD')
    s2.cmd('ovs-ofctl add-flow s2 priority=1,arp,actions=FLOOD')
    s3.cmd('ovs-ofctl add-flow s3 priority=1,arp,actions=FLOOD')
    
    # High priority flow (h1 to h3) - Queue 1 (5-8 Mbps)
    s1.cmd('ovs-ofctl add-flow s1 priority=3,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=set_queue:1,output:"s1-eth3"')
    s2.cmd('ovs-ofctl add-flow s2 priority=3,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=output:"s2-eth1"')
    
    # Medium priority flow (h2 to h4) - Queue 2 (2-5 Mbps)
    s1.cmd('ovs-ofctl add-flow s1 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=set_queue:2,output:"s1-eth3"')
    s2.cmd('ovs-ofctl add-flow s2 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=output:"s2-eth3"')
    s3.cmd('ovs-ofctl add-flow s3 priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4,actions=output:"s3-eth1"')

    info('*** Running CLI\n')
    CLI(net)
    
    # Clean up QoS configurations before stopping
    info('*** Cleaning up QoS configurations\n')
    s1.cmd('ovs-vsctl clear Port s1-eth1 qos')
    s1.cmd('ovs-vsctl --all destroy QoS')
    s1.cmd('ovs-vsctl --all destroy Queue')
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    createIoTNetwork()
