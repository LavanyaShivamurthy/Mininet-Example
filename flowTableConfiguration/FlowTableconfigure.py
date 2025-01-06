""" 
  This is minnet Program to create topology with : Controller --1
                                                     switch --4
                                                     host -- 6
    
"""
"""
V1 : Adding Analysis Functions
"""

"""
V2 : Adding TCP Dump Functions
"""
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import os
import time
from time import sleep

                
                
class TopoOF13(Topo):
    def build(self):
        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')

        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', protocols='OpenFlow13')
        
        """
        # Add host links with QoS parameters
        self.addLink(h1, s1, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h2, s1, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h3, s2, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h4, s3, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h5, s4, cls=TCLink, bw=10, delay='5ms', loss=1)
        self.addLink(h6, s4, cls=TCLink, bw=10, delay='5ms', loss=1)
                          
        # Switch interconnections with higher bandwidth
        self.addLink(s1, s2, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s2, s3, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s3, s4, cls=TCLink, bw=20, delay='2ms', loss=0)
        self.addLink(s1, s4, cls=TCLink, bw=20, delay='2ms', loss=0)
        """
        self.addLink(h1, s1, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
        self.addLink(h2, s1, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
        self.addLink(h3, s2, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
        self.addLink(h4, s3, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
        self.addLink(h5, s4, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)
        self.addLink(h6, s4, bw=10, delay='5ms', loss=1, use_htb=True, r2q=1)

        # Switch interconnections with higher bandwidth
        # T add link with bandwidth  in Gbps (multiply by 10 to convert from Gbps to mbps)
        self.addLink(s2, s3, bw=200, delay='2ms', loss=0,use_htb=True,r2q=1)
        self.addLink(s3, s4, bw=200, delay='2ms', loss=0,use_htb=True,r2q=1)
        self.addLink(s1, s4, bw=200, delay='2ms', loss=0,use_htb=True,r2q=1)




def configure_switch_of13(switch):
    """Configure switch to use OpenFlow 1.3 and set up QoS"""
    print(f"Configuring {switch.name} for OpenFlow 1.3")
    
    # Set OpenFlow 1.3
    switch.cmd('ovs-vsctl set Bridge', switch, 'protocols=OpenFlow13')
    
    # Clear existing QoS configurations
    for port in range(1, 5):  # Support up to 4 ports per switch
        switch.cmd(f'ovs-vsctl clear Port {switch.name}-eth{port} qos')
    
    # Configure QoS for each port with three queues
    for port in range(1, 5):
        cmd = f'''ovs-vsctl -- \
                set Port {switch.name}-eth{port} qos=@newqos -- \
                --id=@newqos create QoS type=linux-htb \
                queues:0=@q0 \
                queues:1=@q1 \
                queues:2=@q2 -- \
                --id=@q0 create Queue other-config:min-rate=1000000 \
                                               other-config:max-rate=10000000 -- \
                --id=@q1 create Queue other-config:min-rate=5000000 \
                                               other-config:max-rate=15000000 -- \
                --id=@q2 create Queue other-config:min-rate=3000000 \
                                               other-config:max-rate=20000000'''
        switch.cmd(cmd)

def add_openflow_rules(switch):
    """Add OpenFlow rules to the switch"""
    print(f"\nAdding OpenFlow rules to {switch.name}")
    
    # Clear existing flows
    switch.cmd('ovs-ofctl -O OpenFlow13 del-flows', switch)
    
    # Add table-miss flow entry
    switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, 
              'table=0,priority=0,actions=CONTROLLER:65535')
    
    # Add flow rules for different traffic types
    flow_rules = [
        # ARP and LLDP flooding
        'priority=65535,arp,actions=FLOOD',
        'priority=65535,dl_type=0x88cc,actions=FLOOD',
        
        # ICMP traffic (high priority)
        'priority=10000,ip,nw_proto=1,actions=set_queue:2,FLOOD',
        
        # TCP traffic (medium priority)
        'priority=9000,tcp,actions=set_queue:1,FLOOD',
        
        # UDP traffic (low priority)
        'priority=8000,udp,actions=set_queue:0,FLOOD',
        
        # Default rule for remaining IP traffic
        'priority=5000,ip,actions=set_queue:0,FLOOD'
    ]
    
    # Add each rule
    for rule in flow_rules:
        switch.cmd('ovs-ofctl -O OpenFlow13 add-flow', switch, rule)


    # Verify flows
    print(f"\nVerifying flows on {switch.name}:")
    print(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows', switch))


def configure_htb_qdisc(switch, interface):
    """
    Configures HTB qdisc on a specific interface of a given switch in Mininet.

    :param switch: Mininet switch object (e.g., s1)
    :param interface: Interface name as a string (e.g., 's1-eth1')
    """
    command_1= f"tc qdisc del dev {interface} root"
    command_2 = f"tc qdisc add dev {interface} root handle 1: htb default 1"
    command_3 =f"tc class add dev {interface}  parent 1: classid 1:1 htb rate 10mbit burst 15k quantum 1500"
    switch.cmd(command_1)
    switch.cmd(command_2)
    switch.cmd(command_3)

def test_network(net):
    """Test network connectivity and QoS"""
    print("\nTesting network connectivity:")
    
    # Get hosts
    h1, h2, h3, h4, h5, h6 = net.get('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
    
    # Test ping between various hosts
    print("\nTesting ping between hosts:")
    pairs = [(h1, h4), (h2, h5), (h3, h6)]
   
    for src, dst in pairs:
        print(f"\nPing from {src.name} to {dst.name}:")
        # Make sure there are no hanging commands
        src.waitOutput()
        dst.waitOutput()
        
        try:
            # Run ping command and wait for output
            ping_result = src.cmd(f'ping -c 3 {dst.IP()}')
            print(ping_result)
        except Exception as e:
            print(f"Error during ping test between {src.name} and {dst.name}: {e}")
            
        # Ensure commands are finished before proceeding
        src.waitOutput()
        dst.waitOutput()
    
    # Test bandwidth between hosts using iperf
    print("\nTesting bandwidth between hosts:")
    for src, dst in pairs:
        print(f"\nBandwidth test from {src.name} to {dst.name}:")
        
        # Make sure there are no hanging commands
        src.waitOutput()
        dst.waitOutput()
        
        try:
            # Start iperf server with specific pid file
            dst.cmd('iperf -s > /dev/null 2>&1 & echo $! > /tmp/iperf_server.pid')
            # Wait a moment for server to start
            time.sleep(2)
            
            # Run iperf client
            iperf_result = src.cmd(f'iperf -c {dst.IP()} -t 5')
            print(iperf_result)
            
            # Cleanup iperf server
            dst.cmd('kill $(cat /tmp/iperf_server.pid)')
            dst.cmd('rm -f /tmp/iperf_server.pid')
            
            # Additional cleanup to ensure iperf is fully terminated

            dst.cmd("pkill -9 iperf")
            print("Cleaned up all iperf Process")

        except Exception as e:
            print(f"Error during bandwidth test between {src.name} and {dst.name}: {e}")
            # Cleanup in case of error
            dst.cmd("pkill -9 iperf")
        
        # Ensure commands are finished before proceeding
        src.waitOutput()
        dst.waitOutput()
        
        # Small delay between tests
        time.sleep(1)
        



def main():
    setLogLevel('info')
    
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    os.system('pkill -f tcpdump')  # Add this line to clean up any lingering tcpdump processes
    
    print("Starting QoS network with statistics monitoring")
    
    # Initialize network and statistics collector
    topo = TopoOF13()
    
    # Create and start network
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=Controller,
        link=TCLink,
        autoSetMacs=True
    )
    
    net.start()
    print("Waiting for network to initialize...")
    sleep(2)

    # Configure switches and add flows
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)

    for switch in net.switches:


    #configure Switch and Fix HTB settings using tc
    print("Adjusting HTB parameters...")

        

if __name__ == '__main__':
    main()
