#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
import time

def createNetwork():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add switches and hosts
    s1 = net.addSwitch('s1')
    h1 = net.addHost('h1')
    
    # Set OpenFlow 1.3
    s1.cmd('ovs-vsctl set Bridge {} protocols=OpenFlow13'.format(s1.name))
    
    # Add link with minimum r2q
    net.addLink(h1, s1, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
    
    # Start network
    net.build()
    c0.start()
    s1.start([c0])
    
    # Wait for links to be established
    time.sleep(1)
    
    # Fix HTB settings using tc
    print("Adjusting HTB parameters...")
    
    # Set quantum to MTU size (typically 1500 bytes)
    h1.cmd('tc qdisc del dev h1-eth0 root')
    h1.cmd('tc qdisc add dev h1-eth0 root handle 1: htb default 1')
    h1.cmd('tc class add dev h1-eth0 parent 1: classid 1:1 htb rate 10mbit burst 15k quantum 1500')
    
    s1.cmd('tc qdisc del dev s1-eth1 root')
    s1.cmd('tc qdisc add dev s1-eth1 root handle 1: htb default 1')
    s1.cmd('tc class add dev s1-eth1 parent 1: classid 1:1 htb rate 10mbit burst 15k quantum 1500')
    
    print("HTB parameters adjusted successfully")
    
    return net

if __name__ == '__main__':
    setLogLevel('info')
    net = createNetwork()
    CLI(net)
    net.stop()
