from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

import json
import random
import time
from threading import Thread
import paho.mqtt.client as mqtt
import subprocess

class MQTTBroker:
    def __init__(self, node):
        self.node = node
        
    def start(self):
        """Start Mosquitto MQTT broker on the node"""
        # Stop any existing mosquitto process
        self.node.cmd('pkill mosquitto')
        time.sleep(1)
        
        # Configure mosquitto to listen on all interfaces and enable verbose logging
        config = """
listener 1883 0.0.0.0
allow_anonymous true
log_type all
"""
        self.node.cmd(f'echo "{config}" > /tmp/mosquitto.conf')
        
        # Start broker with verbose logging
        self.node.cmd('mosquitto -c /tmp/mosquitto.conf -v > /tmp/mosquitto.log 2>&1 &')
        time.sleep(2)
        
        # Verify broker is running and listening
        ps_out = self.node.cmd('ps aux | grep mosquitto | grep -v grep')
        netstat_out = self.node.cmd('netstat -tln | grep :1883')
        
        info(f'*** Mosquitto process status:\n{ps_out}\n')
        info(f'*** Mosquitto port status:\n{netstat_out}\n')
        
        if '1883' not in netstat_out:
            info('*** Warning: Mosquitto not listening on port 1883\n')
            info('*** Mosquitto log:\n')
            info(self.node.cmd('cat /tmp/mosquitto.log'))
            return False
            
        info(f'*** Started MQTT broker on {self.node.name} at {self.node.IP()}\n')
        return True
        
    def stop(self):
        """Stop the MQTT broker"""
        self.node.cmd('pkill mosquitto')

def verify_network(net, broker_node):
    """Verify network connectivity and broker accessibility"""
    info('*** Verifying network configuration\n')
    
    # Test basic connectivity
    if net.pingAll() != 0:
        info('*** Warning: Some nodes are not reachable\n')
        return False
        
    # Verify broker node configuration
    broker_ip = broker_node.IP()
    info(f'*** Broker IP: {broker_ip}\n')
    
    # Check if broker port is accessible from other nodes
    for host in net.hosts:
        if host != broker_node:
            test_cmd = f"timeout 1 nc -zv {broker_ip} 1883"
            result = host.cmd(test_cmd)
            info(f'*** Testing MQTT port from {host.name}: {result}\n')
    
    return True

def create_iot_network():
    net = Mininet(controller=Controller, switch=OVSKernelSwitch, link=TCLink)
    
    info('*** Adding controller\n')
    net.addController('c0')
    
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')
    
    info('*** Adding broker node\n')
    broker_node = net.addHost('broker')
    net.addLink(broker_node, s1)
    
    info('*** Adding data collector node\n')
    collector_node = net.addHost('collector')
    net.addLink(collector_node, s1)
    
    info('*** Adding IoT nodes\n')
    iot_nodes = []
    
    # Add temperature sensors
    for i in range(3):
        node = net.addHost(f'temp{i}')
        net.addLink(node, s1)
        iot_nodes.append((node, "temperature"))
    
    # Add humidity sensors
    for i in range(2):
        node = net.addHost(f'hum{i}')
        net.addLink(node, s1)
        iot_nodes.append((node, "humidity"))
    
    info('*** Starting network\n')
    net.start()
    
    # Verify network connectivity
    if not verify_network(net, broker_node):
        info('*** Network verification failed\n')
        return None, None, None, None
    
    # Start MQTT broker
    broker = MQTTBroker(broker_node)
    if not broker.start():
        info('*** Failed to start MQTT broker\n')
        return None, None, None, None
    
    return net, broker_node, collector_node, iot_nodes

if __name__ == '__main__':
    setLogLevel('info')
    
    # Create and start the network with initial components
    net, broker_node, collector_node, iot_nodes = create_iot_network()

    
    if net is None:
        info('*** Failed to create network\n')
        exit(1)
    
    try:
        # Manual testing of MQTT connectivity
        info('*** Testing MQTT connectivity\n')
        
        # Test subscriber
        collector_node.cmd('mosquitto_sub -h 10.0.0.1 -t "test" -C 1 > /tmp/sub_test &')
        time.sleep(1)
        
        # Test publisher
        broker_node.cmd('mosquitto_pub -h 10.0.0.1 -t "test" -m "tesr message"')
        time.sleep(1)
        
        # Check if message was received
        test_result = collector_node.cmd('cat /tmp/sub_test')
        info(f'*** MQTT test result: {test_result}\n')
        
        if 'tesr message' in test_result:
            info('*** MQTT test successful\n')
        else:
            info('*** MQTT test failed\n')
            raise Exception("MQTT connectivity test failed")
        if not verify_network(net, broker_node):
            info('*** Network verification failed..Main\n')
        else:

            info('*** Network verification Sucess Main\n')

        # Start CLI for manual testing
        CLI(net)
        
    finally:
        if net:
            net.stop()
