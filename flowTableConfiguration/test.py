from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import time
from time import sleep

class customTopology(Topo):
    def build(self):

        info('*** Adding switches\n')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')

        info('*** Adding medical devices/hosts\n')
        # Emergency Alert Devices
        emergency = self.addHost('emergency', ip='10.0.0.10')
        # Patient Monitoring Devices
        monitoring = self.addHost('monitoring', ip='10.0.0.20')
        # Medical Imaging Devices
        imaging = self.addHost('imaging', ip='10.0.0.30')
        # Medical Device Host
        med_device = self.addHost('med_device', ip='10.0.0.40')
        # Administrative System
        admin = self.addHost('admin', ip='10.0.0.50')
        # Environmental Sensors
        env_sensor = self.addHost('env_sensor', ip='10.0.0.60')

        # Server to receive all traffic
        server = self.addHost('server', ip='10.0.0.100')
        info('*** Creating links with QoS\n')
        # Links with different bandwidth and latency requirements
        self.addLink(emergency, s1, cls=TCLink, bw=10)  # , delay='2ms', max_queue_size=1000)
        self.addLink(monitoring, s1, cls=TCLink, bw=10)  # , delay='5ms', max_queue_size=1000)
        self.addLink(imaging, s1, cls=TCLink, bw=10)  # , delay='10ms', max_queue_size=1000)
        self.addLink(med_device, s2, cls=TCLink, bw=10)  # , delay='20ms', max_queue_size=1000)
        self.addLink(admin, s2, cls=TCLink, bw=10)  # , delay='50ms', max_queue_size=1000)
        self.addLink(env_sensor, s2, cls=TCLink, bw=10)  # , delay='100ms', max_queue_size=1000)
        self.addLink(server, s3, cls=TCLink, bw=10)  # , delay='1ms', max_queue_size=1000)
        # Inter-switch links
        self.addLink(s1, s2, cls=TCLink, bw=15, delay='1ms')
        self.addLink(s2, s3, cls=TCLink, bw=15, delay='1ms')

def configure_switches(switch):
    info('*** Configuring QoS\n')
    # Configure QoS queues on switches
    # Queue configuration for s1
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
"""
Start generating traffic 
"""
def generate_emergency_alerts(host, destination, duration=60):
    """Generate emergency alert traffic"""
    while True:
        # Small packets (100 bytes) with highest priority
        host.cmd(f'ping -c 1 -s 100 -Q 0x28 {destination} &')
        time.sleep(random.uniform(0.5, 2.0))  # Random intervals

def generate_patient_monitoring(host, destination, duration=60):
    """Generate continuous patient monitoring data"""
    # Use iperf for continuous stream with specific QoS
    host.cmd(f'iperf -c {destination} -t {duration} -u -b 2M -Q 0x20 &')

def generate_medical_imaging(host, destination, duration=60):
    """Generate large medical imaging data"""
    # Large data transfer with high bandwidth
    host.cmd(f'iperf -c {destination} -t {duration} -b 50M -Q 0x18 &')



def main():
    setLogLevel('info')  # Enable Mininet logs
    # Clean up any previous run
    os.system('mn -c')
    os.system('killall controller')
    os.system('pkill -f tcpdump')  # Add this line to clean up any lingering tcpdump processes

    # Initialize network and statistics collector
    topo = customTopology()
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
    sleep(5)

  # Access switches in the network
    for switch in net.switches:
        print(f"Switch: {switch.name}")
        for intf in switch.intfList():
            print(f"  Interface: {intf.name}")
    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()



if __name__ == '__main__':
    main()


