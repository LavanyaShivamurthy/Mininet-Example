from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
import csv
from datetime import datetime
import time
from time import sleep
import threading
import json
from collections import defaultdict
import psutil
import subprocess
import os
# ... (Previous NetworkStats and NetworkMonitor classes remain the same) ...
class NetworkStats:
    def __init__(self, csv_output_dir='network_stats'):
        self.stats = defaultdict(lambda: {
            'bytes_sent': 0,
            'bytes_recv': 0,
            'packets_sent': 0,
            'packets_recv': 0,
            'bandwidth_history': [],
            'latency_history': []
        })
        self.lock = threading.Lock()
        self.csv_output_dir = csv_output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(csv_output_dir, exist_ok=True)
        
        # Initialize CSV files with headers
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialize CSV files with headers"""
        # Traffic stats CSV
        with open(f'{self.csv_output_dir}/traffic_stats.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'link', 'bytes_sent', 'bytes_recv', 
                           'packets_sent', 'packets_recv'])
        
        # Bandwidth CSV
        with open(f'{self.csv_output_dir}/bandwidth.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'link', 'bandwidth_mbps'])
        
        # Latency CSV
        with open(f'{self.csv_output_dir}/latency.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'link', 'latency_ms'])

    def update_stats(self, node1, node2, bytes_sent, bytes_recv, packets_sent, packets_recv):
        with self.lock:
            key = f"{node1}-{node2}"
            timestamp = datetime.now().isoformat()
            
            if bytes_sent >= 0 and bytes_recv >= 0 and packets_sent >= 0 and packets_recv >= 0:
                self.stats[key]['bytes_sent'] += bytes_sent
                self.stats[key]['bytes_recv'] += bytes_recv
                self.stats[key]['packets_sent'] += packets_sent
                self.stats[key]['packets_recv'] += packets_recv
                
                # Write to CSV
                with open(f'{self.csv_output_dir}/traffic_stats.csv', 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, key, bytes_sent, bytes_recv, 
                                   packets_sent, packets_recv])

    def add_bandwidth_measurement(self, node1, node2, bandwidth):
        with self.lock:
            key = f"{node1}-{node2}"
            timestamp = datetime.now().isoformat()
            
            self.stats[key]['bandwidth_history'].append({
                'timestamp': time.time(),
                'bandwidth': bandwidth
            })
            
            # Write to CSV
            with open(f'{self.csv_output_dir}/bandwidth.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, key, bandwidth])

    def add_latency_measurement(self, node1, node2, latency):
        with self.lock:
            key = f"{node1}-{node2}"
            timestamp = datetime.now().isoformat()
            
            self.stats[key]['latency_history'].append({
                'timestamp': time.time(),
                'latency': latency
            })
            
            # Write to CSV
            with open(f'{self.csv_output_dir}/latency.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, key, latency])
                
class TCPDumpCollector:
    def __init__(self, net, output_dir='tcpdump_data'):
        self.net = net
        self.output_dir = output_dir
        self.processes = {}
        os.makedirs(output_dir, exist_ok=True)
    
    def start_capture(self, node, interface=None, filter_str=None):
        """Start tcpdump capture on a node"""
        if isinstance(node, str):
            node = self.net.get(node)
        
        # If no interface specified, capture on all interfaces
        if interface is None:
            interfaces = [intf.name for intf in node.intfs.values() if intf.name != 'lo']
        else:
            interfaces = [interface]
        
        for intf in interfaces:
            try:
                # Create filename based on node, interface and timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{self.output_dir}/{node.name}_{intf}_{timestamp}.pcap'
                
                # Build tcpdump command using pgrep to get PID reliably
                cmd = f'tcpdump -i {intf} -w {filename}'
                if filter_str:
                    cmd += f' "{filter_str}"'
                
                # Start tcpdump in background
                node.cmd(f'{cmd} > /dev/null 2>&1 &')
                
                # Get PID using pgrep
                pid_output = node.cmd(f"pgrep -f 'tcpdump -i {intf}'")
                
                # Extract PID from output
                try:
                    pid = int(pid_output.strip().split('\n')[0])
                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not get PID for tcpdump on {node.name} {intf}, using placeholder")
                    pid = -1
                
                self.processes[(node.name, intf)] = {
                    'pid': pid,
                    'file': filename
                }
                print(f"Started tcpdump on {node.name} interface {intf}, saving to {filename} (PID: {pid})")
                
            except Exception as e:
                print(f"Error starting tcpdump on {node.name} interface {intf}: {e}")
    
    def stop_capture(self, node=None, interface=None):
        """Stop tcpdump capture"""
        if node:
            if isinstance(node, str):
                node_name = node
            else:
                node_name = node.name
            
            # Stop specific interface or all interfaces for the node
            to_stop = [(n, i) for n, i in self.processes.keys() 
                      if n == node_name and (interface is None or i == interface)]
        else:
            # Stop all captures
            to_stop = list(self.processes.keys())
        
        for node_name, intf in to_stop:
            try:
                process = self.processes.pop((node_name, intf))
                node = self.net.get(node_name)
                
                # Kill tcpdump process more reliably
                if process['pid'] != -1:
                    node.cmd(f'kill {process["pid"]}')
                
                # Backup method to ensure tcpdump is stopped
                node.cmd(f"pkill -f 'tcpdump -i {intf}'")
                
                print(f"Stopped tcpdump on {node_name} interface {intf}")
                print(f"Capture saved to {process['file']}")
                
            except Exception as e:
                print(f"Error stopping tcpdump on {node_name} interface {intf}: {e}")
    
    def cleanup(self):
        """Cleanup all tcpdump processes"""
        try:
            # Stop all captures
            self.stop_capture()
            
            # Additional cleanup to ensure no tcpdump processes remain
            for node in self.net.hosts:
                node.cmd('pkill -f tcpdump')
            
            print("Cleaned up all tcpdump processes")
            
        except Exception as e:
            print(f"Error during tcpdump cleanup: {e}")


                
                
class ExpandedQoSTopoOF13(Topo):
    def build(self):
        # Create hosts and switches (same as before)
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
        
        # Add links with QoS parameters and store link information
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

class NetworkMonitor:
    def __init__(self, net, stats_collector):
        self.net = net
        self.stats_collector = stats_collector
        self.running = False
        self.monitor_thread = None
        self.prev_stats = {}

    def get_interface_stats(self, node, interface):
        """Get interface statistics using ip tool instead of ifconfig"""
        # Use ip -s link show instead of ifconfig for more reliable stats
        output = node.cmd(f'ip -s link show {interface}')
        rx_bytes = tx_bytes = rx_packets = tx_packets = 0
        
        try:
            lines = output.split('\n')
            # RX stats are typically on line 3, TX stats on line 5
            if len(lines) >= 5:
                # Parse RX stats
                rx_stats = lines[3].strip().split()
                if len(rx_stats) >= 2:
                    rx_bytes = int(rx_stats[0])
                    rx_packets = int(rx_stats[1])
                
                # Parse TX stats
                tx_stats = lines[5].strip().split()
                if len(tx_stats) >= 2:
                    tx_bytes = int(tx_stats[0])
                    tx_packets = int(tx_stats[1])
                
                # Print debug information
                print(f"Interface {interface} stats - RX: {rx_bytes} bytes, {rx_packets} packets, TX: {tx_bytes} bytes, {tx_packets} packets")
        except Exception as e:
            print(f"Error parsing interface stats for {interface}: {e}")
            
        return rx_bytes, tx_bytes, rx_packets, tx_packets

    def measure_bandwidth(self, source, target, duration=2):
        """Measure bandwidth between two hosts using iperf"""
        try:
            # Start iperf server with specific pid file
            target.cmd('iperf -s -p 5001 > /dev/null 2>&1 & echo $! > /tmp/iperf_server.pid')
            time.sleep(0.5)
            
            # Run iperf client
            output = source.cmd(f'iperf -c {target.IP()} -t {duration} -p 5001')
            
            # Cleanup server
            target.cmd('kill $(cat /tmp/iperf_server.pid)')
            target.cmd('rm -f /tmp/iperf_server.pid')
            target.cmd('pkill -9 iperf')
            
            # Parse bandwidth
            if 'Mbits/sec' in output:
                bandwidth = float(output.split('Mbits/sec')[0].split()[-1])
                print(f"Measured bandwidth between {source.name} and {target.name}: {bandwidth} Mbits/sec")
                return bandwidth
        except Exception as e:
            print(f"Error measuring bandwidth between {source.name} and {target.name}: {e}")
        
        return 0

    def measure_latency(self, source, target):
        """Measure latency between two hosts using ping"""
        try:
            source.waitOutput()
            output = source.cmd(f'ping -c 1 -w 2 {target.IP()}')
            if 'time=' in output:
                latency = float(output.split('time=')[1].split()[0])
                print(f"Measured latency between {source.name} and {target.name}: {latency} ms")
                return latency
        except Exception as e:
            print(f"Error measuring latency between {source.name} and {target.name}: {e}")
        
        return 0

    def monitor_network(self):
        """Monitor network statistics"""
        while self.running:
            try:
                # Monitor interface statistics
                for host in self.net.hosts:
                    for intf in host.intfs.values():
                        if intf.name != 'lo' and intf.link:  # Ensure interface has a link
                            current_stats = self.get_interface_stats(host, intf.name)
                            
                            if intf.name in self.prev_stats:
                                prev_vals = self.prev_stats[intf.name]
                                bytes_recv_delta = max(0, current_stats[0] - prev_vals[0])
                                bytes_sent_delta = max(0, current_stats[1] - prev_vals[1])
                                packets_recv_delta = max(0, current_stats[2] - prev_vals[2])
                                packets_sent_delta = max(0, current_stats[3] - prev_vals[3])
                                
                                # Get the name of the connected node
                                connected_node = intf.link.intf2.node.name
                                
                                # Update statistics
                                self.stats_collector.update_stats(
                                    host.name, connected_node,
                                    bytes_sent_delta, bytes_recv_delta,
                                    packets_sent_delta, packets_recv_delta
                                )
                            
                            self.prev_stats[intf.name] = current_stats
                
                # Measure bandwidth and latency between select hosts
                for h1 in self.net.hosts[::2]:  # Sample subset of hosts
                    for h2 in self.net.hosts[1::2]:
                        if h1 != h2:
                            h1.waitOutput()
                            h2.waitOutput()
                            
                            bandwidth = self.measure_bandwidth(h1, h2)
                            self.stats_collector.add_bandwidth_measurement(h1.name, h2.name, bandwidth)
                            
                            time.sleep(0.5)  # Short delay between measurements
                            
                            latency = self.measure_latency(h1, h2)
                            self.stats_collector.add_latency_measurement(h1.name, h2.name, latency)
                
            except Exception as e:
                print(f"Error in monitor_network: {e}")
            
            time.sleep(5)  # Update interval

    def start_monitoring(self):
        """Start the monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_network)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("Network monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Network monitoring stopped")

def print_network_stats(stats_collector):
    """Print current network statistics"""
    stats = stats_collector.get_stats()
    print("\nNetwork Statistics:")
    print("=" * 80)
    

    for link, data in stats.items():
        print(f"\nLink: {link}")
        print("-" * 40)
        print(f"Total Bytes Sent: {data['bytes_sent']:,} bytes")
        print(f"Total Bytes Received: {data['bytes_recv']:,} bytes")
        print(f"Total Packets Sent: {data['packets_sent']:,}")
        print(f"Total Packets Received: {data['packets_recv']:,}")
        
        if data['bandwidth_history']:
            recent_bandwidth = data['bandwidth_history'][-1]['bandwidth']
            print(f"Current Bandwidth: {recent_bandwidth:.2f} Mbps")
            
        if data['latency_history']:
            recent_latency = data['latency_history'][-1]['latency']
            print(f"Current Latency: {recent_latency:.2f} ms")



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
    topo = ExpandedQoSTopoOF13()
    stats_collector = NetworkStats(csv_output_dir='network_stats')
    
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
    
    # Initialize TCPDump collector
    tcpdump_collector = TCPDumpCollector(net, output_dir='tcpdump_data')
    
    # Configure switches and add flows
    for switch in net.switches:
        configure_switch_of13(switch)
        add_openflow_rules(switch)
    
    try:
        # Start tcpdump on all hosts
        for host in net.hosts:
            tcpdump_collector.start_capture(host)
        
        # Initialize and start network monitor
        monitor = NetworkMonitor(net, stats_collector)
        monitor.start_monitoring()
        
        # Add custom commands to Mininet CLI
        CLI.do_showstats = lambda self, _: print_network_stats(stats_collector)
        CLI.do_stoptcpdump = lambda self, _: tcpdump_collector.stop_capture()
        
        print("\nNetwork is ready.")
        print("Available commands:")
        print("  showstats - Show current network statistics")
        print("  stoptcpdump - Stop all tcpdump captures")
        CLI(net)
        
    except Exception as e:
        print(f"Error during network operation: {e}")
        
    finally:
        # Cleanup
        print("Cleaning up...")
        tcpdump_collector.cleanup()
        monitor.stop_monitoring()
        net.stop()
        os.system('pkill -f tcpdump')  # Final cleanup of any remaining tcpdump processes

if __name__ == '__main__':
    main()
