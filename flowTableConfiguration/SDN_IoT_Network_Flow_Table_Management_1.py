"""

key components and configurations in the SDN IoT network demonstration:

    Network Topology:
         3 switches (s1, s2, s3) connected in a line: s1 ↔ s2 ↔ s3
         4 IoT devices (hosts) connected as follows:
            h1 and h2 connected to s1
            h3 connected to s2
            h4 connected to s3

        IP addressing: All hosts are in the 10.0.0.0/8 network

        h1: 10.0.0.1
        h2: 10.0.0.2
        h3: 10.0.0.3
        h4: 10.0.0.4
    Controller Configuration:
        pythonCopynet = Mininet(topo=None,
              build=False,
              ipBase='10.0.0.0/8',
              controller=Controller)

        Using Mininet's default controller
        The controller handles basic switching functionality
        No external SDN controller needed

    Flow Table Rules:
        There are two types of flow rules configured:

        a. ARP Handling:
            s1.cmd('ovs-ofctl add-flow s1 priority=1,arp,actions=flood')
                    Priority 1 (lower priority)
                    Floods ARP packets to all ports
                    Helps hosts discover each other's MAC addresses
        Applied to all switches

        b. Specific Traffic Flows:
        
        # h1 to h3 traffic
            s1.cmd('ovs-ofctl add-flow s1 priority=2,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=output:3')
            s2.cmd('ovs-ofctl add-flow s2 priority=2,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3,actions=output:1')

            Priority 2 (higher priority)
            Defines specific paths for IP traffic between hosts
                    For example, traffic from h1 (10.0.0.1) to h3 (10.0.0.3):
                            On s1: Output to port 3 (towards s2)
                            On s2: Output to port 1 (towards h3)

        Testing the Configuration:
                In the Mininet CLI, you can:
    
            # View flow tables on each switch
                sh ovs-ofctl dump-flows s1
                sh ovs-ofctl dump-flows s2
                sh ovs-ofctl dump-flows s3

            # Test connectivity
                    pingall
                    h1 ping h3
                    h2 ping h4

            Flow Rule Format Explanation:

                ovs-ofctl add-flow [switch] priority=[num],ip,nw_src=[source_ip],nw_dst=[dest_ip],actions=output:[port_num]

                    priority: Determines rule precedence (higher number = higher priority)
                    ip: Matches IP packets
                    nw_src: Source IP address
                    nw_dst: Destination IP address
                    actions=output: Specifies the output port

                Static High Priority Rules (Priority=2):

                    priority=2,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3 actions=output:"s1-eth3"
                    priority=2,ip,nw_src=10.0.0.2,nw_dst=10.0.0.4 actions=output:"s1-eth3"

                These are our manually configured flows for specific host-to-host communication
                Routes traffic from h1→h3 and h2→h4 through s1-eth3 port
                Has seen actual traffic (n_packets=5 and n_packets=2 respectively)


            ARP Rule (Priority=1):

                priority=1,arp actions=FLOOD

                    Handles ARP packets by flooding them to all ports
                    Has been active (n_packets=24), showing ARP discovery is working
                Dynamically Added ICMP Rules (Priority=1):

                    priority=1,icmp,in_port="s1-eth1",....actions=output:"s1-eth2"

            These are automatically added by the controller for PING (ICMP) traffic
                    Include detailed match fields:

                    in_port: Source port
                    dl_src/dl_dst: MAC addresses
                    nw_src/nw_dst: IP addresses
                    icmp_type: 8 (request) or 0 (reply)
                    Have idle_timeout=60 (remove after 60 seconds of inactivity)


                Default Rule (Priority=0):

                        priority=0 actions=CONTROLLER:128

                Lowest priority catch-all rule
                        Sends unmatched packets to the controller
                        Has handled significant traffic (n_packets=91)

                Key Statistics in Each Entry:

                duration: How long the rule has existed
                n_packets: Number of packets matched
                n_bytes: Total bytes matched
                cookie: Identifier for the flow (0x0 means default)
                table=0: All rules are in the first flow table

    The output shows:

        Our static rules are working (traffic going through them)
        ARP flooding is active and being used
        The controller is dynamically adding specific ICMP rules for ping traffic
        known traffic is being handled by the controller as expected
The flow table demonstrates both proactive (our static rules) and reactive (controller-added ICMP rules) flow management working together in the network.
"""

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
