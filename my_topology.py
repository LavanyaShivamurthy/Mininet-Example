from mininet.topo import Topo

class IoTTopo(Topo):
    def build(self):
        # Add a controller (assumed to be external)
        # Add switches
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')

        # Add IoT hosts (sensor nodes)
        sensor1 = self.addHost('h1')
        sensor2 = self.addHost('h2')

        # Add data receivers/servers
        server = self.addHost('h3')

        # Links
        self.addLink(switch1, switch2)
        self.addLink(sensor1, switch1)
        self.addLink(sensor2, switch1)
        self.addLink(server, switch2)

topo = IoTTopo()

