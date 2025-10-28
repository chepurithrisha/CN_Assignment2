#!/usr/bin/env python3
"""
CS331 – DNS Query Resolution Topology
Assignment 2
Topology:
H1(10.0.0.1) – S1 – S2 – S3 – S4 – H4(10.0.0.4)
                |    |     |
                |    |     H3(10.0.0.3)
                |    |
                |    H2(10.0.0.2)
                |
                DNS Resolver (10.0.0.5)

Link parameters:
- All host links: 100 Mbps, 2 ms
- S1–S2: 100 Mbps, 5 ms
- S2–S3: 100 Mbps, 8 ms
- S3–S4: 100 Mbps, 10 ms
- S2–DNS Resolver: 100 Mbps, 1 ms
"""

from mininet.net import Mininet
from mininet.node import Controller  # Use built-in Python controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def build():
    # Use built-in Controller and TCLink for bandwidth/delay control
    net = Mininet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    c0 = net.addController('c0', controller=Controller)  # Local controller

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    dns = net.addHost('dns', ip='10.0.0.5/24')

    info('*** Creating links\n')
    # Host links
    net.addLink(h1, s1, bw=100, delay='2ms')
    net.addLink(h2, s2, bw=100, delay='2ms')
    net.addLink(h3, s3, bw=100, delay='2ms')
    net.addLink(h4, s4, bw=100, delay='2ms')

    # Inter-switch links
    net.addLink(s1, s2, bw=100, delay='5ms')
    net.addLink(s2, s3, bw=100, delay='8ms')
    net.addLink(s3, s4, bw=100, delay='10ms')

    # DNS resolver link
    net.addLink(dns, s2, bw=100, delay='1ms')

    info('*** Starting network\n')
    net.start()

    info('*** Testing connectivity\n')
    net.pingAll()

    info('*** Network ready. Enter CLI.\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    build()

