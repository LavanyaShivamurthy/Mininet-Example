from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info


def customTopology():
    net = Mininet(topo=None, build=False, link=TCLink)  # Custom topology

    info('*** Adding controller\n')
    c0 = net.addController('c0')

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)

    info('*** Building the network\n')
    net.build()

    info('*** Starting the network\n')
    net.start()

    # Access switches in the network
    for switch in net.switches:
        print(f"Switch: {switch.name}")
        for intf in switch.intfList():
            print(f"  Interface: {intf.name}")

    info('*** Stopping the network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')  # Enable Mininet logs
    customTopology()

