import os
import csv
from scapy.all import ARP, ICMP, TCP, UDP, IP, IPv6, ICMPv6EchoRequest, ICMPv6EchoReply, rdpcap, ICMPv6ND_NS, ICMPv6ND_NA
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

# Configuration
pcap_folder = "/home/ictlab7/Documents/Mininet_Learning/"
output_csv = "bandwidth_usage.csv"
INTERVAL = 0.1  # Time window in seconds

class BandwidthAnalyzer:
    def __init__(self, interval):
        self.interval = interval
        self.stats = defaultdict(lambda: {
            'timestamp': None,
            'TCP': 0,
            'UDP': 0,
            'ICMP': 0,
            'ICMPv6': 0,
            'ARP': 0,
            'Other': 0
        })
        print(f"Initializing bandwidth analysis with {interval} second intervals")

    def process_packet(self, packet, packet_time):
        """Process a single packet and update bandwidth statistics"""
        interval_key = int(packet_time / self.interval) * self.interval
        packet_size = len(packet) * 8  # Convert bytes to bits
        
        # Update timestamp
        if self.stats[interval_key]['timestamp'] is None:
            self.stats[interval_key]['timestamp'] = datetime.fromtimestamp(interval_key).strftime('%Y-%m-%d %H:%M:%S')

        # Classify packet and update bandwidth
        if TCP in packet:
            self.stats[interval_key]['TCP'] += packet_size
        elif UDP in packet:
            self.stats[interval_key]['UDP'] += packet_size
        elif ICMP in packet:
            self.stats[interval_key]['ICMP'] += packet_size
        elif IPv6 in packet and (ICMPv6EchoRequest in packet or ICMPv6EchoReply in packet or 
                                ICMPv6ND_NS in packet or ICMPv6ND_NA in packet):
            self.stats[interval_key]['ICMPv6'] += packet_size
        elif ARP in packet:
            self.stats[interval_key]['ARP'] += packet_size
        else:
            self.stats[interval_key]['Other'] += packet_size

    def analyze_pcap(self, pcap_file):
        """Analyze a PCAP file and calculate bandwidth usage"""
        print(f"Processing {pcap_file}...")
        packets = rdpcap(pcap_file)
        total_packets = len(packets)
        print(f"Loaded {total_packets} packets")
        
        for i, packet in enumerate(packets):
            if i % 10000 == 0:
                print(f"Processed {i}/{total_packets} packets...")
            
            try:
                packet_time = float(packet.time)
                self.process_packet(packet, packet_time)
            except Exception as e:
                print(f"Error processing packet {i}: {e}")
                continue
        
        print(f"Finished processing {total_packets} packets")

    def save_results(self):
        """Save bandwidth statistics to CSV"""
        print(f"Saving results to {output_csv}")
        with open(output_csv, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(['Timestamp', 'TCP_bps', 'UDP_bps', 'ICMP_bps', 'ICMPv6_bps', 'ARP_bps', 'Other_bps'])
            
            # Sort by timestamp and write data
            sorted_times = sorted(self.stats.keys())
            for t in sorted_times:
                stats = self.stats[t]
                # Convert to bits per second
                writer.writerow([
                    stats['timestamp'],
                    stats['TCP'] / self.interval,
                    stats['UDP'] / self.interval,
                    stats['ICMP'] / self.interval,
                    stats['ICMPv6'] / self.interval,
                    stats['ARP'] / self.interval,
                    stats['Other'] / self.interval
                ])

    def plot_bandwidth(self):
        """Create bandwidth usage plots"""
        print("Creating bandwidth plots...")
        # Read data into pandas DataFrame
        df = pd.read_csv(output_csv)
        
        # Create time series plot
        plt.figure(figsize=(15, 8))
        protocols = ['TCP_bps', 'UDP_bps', 'ICMP_bps', 'ICMPv6_bps', 'ARP_bps', 'Other_bps']
        colors = ['b', 'g', 'r', 'c', 'm', 'y']
        
        for protocol, color in zip(protocols, colors):
            plt.plot(df.index, df[protocol], label=protocol, color=color, marker='.', markersize=2)
        
        plt.title(f'Bandwidth Usage Over Time (Interval: {self.interval}s)')
        plt.xlabel('Time Interval')
        plt.ylabel('Bandwidth (bits per second)')
        plt.legend()
        plt.grid(True)
        plt.xticks(range(0, len(df), max(1, len(df)//10)), rotation=45)
        plt.tight_layout()
        
        # Save plot
        plt.savefig('bandwidth_usage.png')
        print("Plot saved as bandwidth_usage.png")
        
        # Create log scale plot for better visualization of smaller values
        plt.figure(figsize=(15, 8))
        for protocol, color in zip(protocols, colors):
            # Add small value to avoid log(0)
            data = df[protocol].apply(lambda x: x + 1)
            plt.semilogy(df.index, data, label=protocol, color=color, marker='.', markersize=2)
        
        plt.title(f'Bandwidth Usage Over Time (Log Scale, Interval: {self.interval}s)')
        plt.xlabel('Time Interval')
        plt.ylabel('Bandwidth (bits per second)')
        plt.legend()
        plt.grid(True)
        plt.xticks(range(0, len(df), max(1, len(df)//10)), rotation=45)
        plt.tight_layout()
        
        # Save log scale plot
        plt.savefig('bandwidth_usage_log.png')
        print("Log scale plot saved as bandwidth_usage_log.png")

def main():
    # Create analyzer instance with specified interval
    analyzer = BandwidthAnalyzer(INTERVAL)
    
    # Process each pcap file in the folder
    for filename in os.listdir(pcap_folder):
        if filename.endswith('.pcap'):
            full_path = os.path.join(pcap_folder, filename)
            try:
                analyzer.analyze_pcap(full_path)
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
                continue
    
    # Save results and create plots
    analyzer.save_results()
    analyzer.plot_bandwidth()
    print(f"Analysis complete. Results saved to {output_csv}")

if __name__ == "__main__":
    main()
