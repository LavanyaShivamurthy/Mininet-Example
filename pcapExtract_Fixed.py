import os
import csv
import debugpy
#from scapy.all import rdpcap
from scapy.all import ARP, ICMP, TCP, UDP, IP, rdpcap
from datetime import datetime

# Folder containing the tcpdump (.pcap) files
pcap_folder = "/home/ictlab7/Documents/Mininet_Learning/"
output_csv = "bandwidth_usage_from_pcap.csv"

# Interval in seconds for bandwidth calculation
interval = 1

# Initialize data structure to store bandwidth usage
protocol_stats = []

# Process each .pcap file in the folder
for pcap_file in os.listdir(pcap_folder):
    if pcap_file.endswith(".pcap"):
        # Read packets from pcap file
        packets = rdpcap(os.path.join(pcap_folder, pcap_file))
        
        # Initialize stats for the current file
        stats = {
            "timestamp": None,
            "icmp": 0,
            "ip_other": 0,  # Non-TCP/UDP/ICMP IP packets
            "tcp": 0,
            "udp": 0,
            "ARP": 0
        }
        start_time = None  # Initialize start_time here
        
        for packet in packets:
            # Get packet timestamp as float
            packet_time = float(packet.time)
            if start_time is None:
                start_time = packet_time
                stats["timestamp"] = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate elapsed time
            elapsed_time = packet_time - start_time
            if elapsed_time >= interval:
                # Append stats to list and reset for the next interval
                protocol_stats.append(stats.copy())
                start_time = packet_time
                stats = {
                    "timestamp": datetime.fromtimestamp(packet_time).strftime("%Y-%m-%d %H:%M:%S"),
                    "icmp": 0,
                    "ip_other": 0,
                    "tcp": 0,
                    "udp": 0,
                    "ARP": 0
                }

            # Increment the byte count for the appropriate protocol
            try:
                    if ICMP in packet:
                        stats["icmp"] += 1
                    elif UDP in packet:
                        stats["udp"] += 1
                    elif TCP in packet:
                        stats["tcp"] += 1
                    elif ARP in packet:
                        stats["ARP"] += 1
                    elif IP in packet:
                        stats["ip_other"] += 1
            except Exception as e:
                    print(f"Error processing packet: {e}")


        # Append any remaining stats for the last interval
        if stats["icmp"] > 0 or stats["ip_other"] > 0 or stats["tcp"] > 0 or stats["udp"] > 0 or stats["ARP"] > 0:
            protocol_stats.append(stats.copy())

# Write results to CSV
with open(output_csv, mode='w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Timestamp", "Protocol", "Bandwidth_Bytes_Per_Second"])
    for stat in protocol_stats:
        writer.writerow([stat["timestamp"], "icmp", stat["icmp"]])
        writer.writerow([stat["timestamp"], "ip_other", stat["ip_other"]])
        writer.writerow([stat["timestamp"], "tcp", stat["tcp"]])
        writer.writerow([stat["timestamp"], "udp", stat["udp"]])
        writer.writerow([stat["timestamp"], "ARP", stat["ARP"]])

print(f"Bandwidth usage has been written to {output_csv}")

