"""
Code working for ping message socket is not working 


"""


from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import time
from time import sleep
from datetime import datetime
import threading
from numpy import random
import signal
import socket
import sys
#Global declaration
server_ip = "10.0.0.1"  # Replace with the destination host's IP
server_port = 5555
sensor_data = "Temperature:25C"


class customTopology(Topo):
    # [Previous topology code remains the same]
    def build(self):
        info('*** Adding switches\n')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        #s2 = self.addSwitch('s2', protocols='OpenFlow13')
        #s3 = self.addSwitch('s3', protocols='OpenFlow13')
        info('*** Adding medical devices/hosts\n')
        emergency = self.addHost('emergency', ip='10.0.0.10')
        monitoring = self.addHost('monitoring', ip='10.0.0.20')
      #  imaging = self.addHost('imaging', ip='10.0.0.30')
       # med_device = self.addHost('med_device', ip='10.0.0.40')
        #admin = self.addHost('admin', ip='10.0.0.50')
        #env_sensor = self.addHost('env_sensor', ip='10.0.0.60')
        server = self.addHost('server', ip='10.0.0.100')

        # Add links
        self.addLink(emergency, s1, cls=TCLink, bw=10)
        self.addLink(monitoring, s1, cls=TCLink, bw=10)
        #self.addLink(imaging, s1, cls=TCLink, bw=10)
        #self.addLink(med_device, s1, cls=TCLink, bw=10)
        #self.addLink(admin, s1, cls=TCLink, bw=10)
        #self.addLink(env_sensor, s1, cls=TCLink, bw=10)
        self.addLink(server, s1, cls=TCLink, bw=10)
        #self.addLink(s1, s1, cls=TCLink, bw=15, delay='1ms')
        #self.addLink(s2, s3, cls=TCLink, bw=15, delay='1ms')


class TCPDumpCollector:
    def __init__(self, net, output_dir='tcpdump_data'):
        self.net = net
        self.output_dir = output_dir
        self.processes = {}
        self.running = True
        os.makedirs(output_dir, exist_ok=True)

    def start_capture(self, node, interface=None, filter_str=None):
        """Start tcpdump capture on a node"""
        try:
            if isinstance(node, str):
                node = self.net.get(node)


            if not node.waiting:  # Check if node is still active
                # If no interface specified, capture on all interfaces
                if interface is None:
                    interfaces = [intf.name for intf in node.intfs.values() if intf.name != 'lo']
                else:
                    interfaces = [interface]
                for intf in interfaces:
                    try:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f'{self.output_dir}/{node.name}_{intf}_{timestamp}.pcap'
                        
                        cmd = f'tcpdump -i {intf} -w {filename}'
                        if filter_str:
                            cmd += f' "{filter_str}"'
                        

                        # Use Popen instead of cmd
                        import subprocess
                        process = subprocess.Popen(
                            f'exec {cmd}',
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid
                        )

                        
                        self.processes[(node.name, intf)] = {
                            'process': process,
                            'file': filename
                        }
                        print(f"Started tcpdump on {node.name} interface {intf}, saving to {filename}")
                    except Exception as e:
                        print(f"Error starting capture on interface {intf}: {e}")
        except Exception as e:
            print(f"Error in start_capture for node {node}: {e}")


    def stop_capture(self, node=None, interface=None):
        """Stop tcpdump capture"""
        try:
            if node:
                if isinstance(node, str):
                    node_name = node
                else:
                    node_name = node.name
                to_stop = [(n, i) for n, i in self.processes.keys()
                           if n == node_name and (interface is None or i == interface)]
            else:
                to_stop = list(self.processes.keys())


            for node_name, intf in to_stop:
                try:
                    process_info = self.processes.pop((node_name, intf))
                    if 'process' in process_info:
                        os.killpg(os.getpgid(process_info['process'].pid), signal.SIGTERM)
                    print(f"Stopped tcpdump on {node_name} interface {intf}")
                except Exception as e:
                    print(f"Error stopping tcpdump on {node_name} interface {intf}: {e}")
        except Exception as e:
            print(f"Error in stop_capture: {e}")
    def cleanup(self):
        """Cleanup all tcpdump processes"""
        try:
            # Stop all captures
            self.stop_capture()
            

            # Kill any remaining tcpdump processes
            os.system('pkill -f tcpdump')
            print("Cleaned up all tcpdump processes")
        except Exception as e:
            print(f"Error during tcpdump cleanup: {e}")
        finally:
            # Final failsafe cleanup
            os.system('pkill -f tcpdump')





# [Rest of the code remains the same as in previous artifact]
def generate_emergency_alerts(host, destination_ip, stop_event):
    while not stop_event.is_set():
        try:
            #print("generate_emergency_alerts")
           # host.cmd(f'ping -c 1 -s 100 -Q 0x28 {destination}')

      	    # Create UDP socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # sock.sendto(sensor_data.encode(), (server_ip, server_port))
            # print(f"Sent: {sensor_data} {destination}")
            time.sleep(random.uniform(0.5, 2.0))
    	    # Sensor data payload
            sensor_data_list = [
           	 "Temperature:25C",
           	 "Humidity:60%",
           	 "Pressure:1013hPa",
           	 "CO2:400ppm"
       	   ]
           # print(f"Sending UDP data to {destination_ip}:{server_port}")
       	    # Continuous sending
            while True:
                for data in sensor_data_list:
                    # Send sensor data
                    sock.sendto(data.encode(), (destination_ip,server_port))
                    #print(f"Sent to {destination_ip}:{server_port} - {data}")
                    time.sleep(1)
                    # Small delay between messages
    
        except Exception as e:
            print(f"Error in emergency alerts: {e}")
            break


def generate_patient_monitoring(host, destination, stop_event):
    while not stop_event.is_set():
        try:
            # print("generate_patient_monitoring ")
            host.cmd(f'ping -c 1 -s 200 -Q 0x20 {destination}')
            time.sleep(random.uniform(0.2, 0.5))
        except Exception as e:
            print(f"Error in patient monitoring: {e}")
            break

def generate_medical_imaging(host, destination, stop_event):
    while not stop_event.is_set():
        try:
            host.cmd(f'dd if=/dev/urandom bs=1M count=10 | nc -w 1 {destination} 5001')
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"Error in medical imaging: {e}")
            break

def setup_netcat_listener(server):
    try:
        server.cmd('nc -lk 5001 > /dev/null &')
    except Exception as e:
        print(f"Error setting up netcat listener: {e}")

def main():
    tcpdump_collector = None
    net = None
    threads = []
    stop_event = threading.Event()

    try:
        setLogLevel('info')
        os.system('mn -c')
        os.system('killall controller')
        os.system('pkill -f tcpdump')

        # Create and start network
        topo = customTopology()
        net = Mininet(topo=topo, switch=OVSSwitch, controller=Controller, link=TCLink, autoSetMacs=True)
        net.start()
        
        print("Waiting for network to initialize...")
        sleep(5)

        # Initialize tcpdump collector
        tcpdump_collector = TCPDumpCollector(net, output_dir='tcpdump_data')

        # Start packet captures first
        print("Starting packet captures...")
        for switch in net.switches:
            tcpdump_collector.start_capture(switch)
     
        for host in net.hosts:
            tcpdump_collector.start_capture(host)

        # Start netcat listener on server
        setup_netcat_listener(net.get('server'))

        # Start traffic generators
        thread_args = [
            (generate_emergency_alerts, 'emergency'),
            (generate_patient_monitoring, 'monitoring')
            #,
           # (generate_medical_imaging, 'imaging')
        ]

        for func, host_name in thread_args:
            thread = threading.Thread(
                target=func,
                args=(net.get(host_name), '10.0.0.100', stop_event)
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()
        sleep(1)
        print("\nNetwork is ready. Press Ctrl+C to exit.")
        CLI(net)

    except KeyboardInterrupt:
        print("\nShutting down network...")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        if stop_event:
            stop_event.set()
        
        if threads:
            for thread in threads:
                thread.join(timeout=2)
        
        if tcpdump_collector:
            tcpdump_collector.cleanup()
        
        if net:
            net.stop()
        
        # Final cleanup
        os.system('pkill -f tcpdump')
        os.system('pkill -f "nc -lk"')

if __name__ == '__main__':
    main()
