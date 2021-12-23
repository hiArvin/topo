# -*- utf-8 -*-

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.util import custom, pmonitor
from mininet.log import setLogLevel,info
from mininet.link import Link, Intf, TCLink

from functools import partial
import time


class MyTopo(Topo):
    def __init__(self, nodeNum,linkSet,bandwidths,losses):
        Topo.__init__(self)

        self.__nodenum = nodeNum
        self.__linkset = linkSet
        self.__bandwidths = bandwidths
        self.__losses = losses

        self.__switches = []
        self.__hosts = []

        self.create_net()
        self.add_hosts()


    '''create the network topo'''

    def create_net(self):
        for i in range(self.__nodenum):
            self.__switches.append(self.addSwitch("s" + str(i + 1)))
        for i in range(len(self.__linkset)):
            node1 = self.__linkset[i][0]
            node2 = self.__linkset[i][1]
            self.addLink(self.__switches[node1], self.__switches[node2], bw=self.__bandwidths[i], delay='5ms',
                         loss=self.__losses[i], max_queue_size=1000)


    '''add host for each switch(node)'''
    def add_hosts(self):
        if self.__nodenum >= 255:
            print("ERROR!!!")
            exit()
        for i in range(self.__nodenum):
            self.__hosts.append(
                self.addHost("h" + str(i + 1), mac=("00:00:00:00:00:%02x" % (i + 1)), ip="10.0.0." + str(i + 1)))
            self.addLink(self.__switches[i], self.__hosts[i], bw=1000, delay='0ms')  # bw here should be large enough

def generate_request(net, src, src_port, dst, dst_port, rtype, demand, rtime, time_step):
    TIME_OUT = 5
    src_host = net.hosts[src]
    dst_host = net.hosts[dst]

    popens = {}
    popens[dst_host] = dst_host.popen(
        "python3 server.py %s %d %d %d %d" % (dst_host.IP(), dst_port, rtime, rtype, time_step))
    time.sleep(0.1)
    popens[src_host] = src_host.popen("python3 client.py %s %d %s %d %d %d %d" % (
    dst_host.IP(), dst_port, src_host.IP(), src_port, demand, rtime, time_step))
    src_popen = popens[src_host]
    dst_popen = popens[dst_host]
    ind = 0
    time_stamp = time.time()
    for host, line in pmonitor(popens):
        if time.time() - time_stamp > TIME_OUT:
            print("Request:", "src:", src, "dst:", dst, "rtype:", rtype, "demand:", demand)
            delay = TIME_OUT * 1000
            throughput = 0
            loss = 1.
            print("time out!")
            break
        if host:
            print("<%s>: %s" % (host.name, line))

            if host == dst_host:
                ret = line.split()
                delay = float(ret[1])
                throughput = float(ret[4])
                loss = float(ret[7])
                # flag = True
                if ind == 1:  # avoid using the first data received from server
                    break
                else:
                    ind += 1

    return delay, throughput, loss, (src_popen, dst_popen)

if __name__ == "__main__":
    nodeNum = 4
    linkSet = [[0, 1], [1, 2], [2, 3], [0, 3]]
    bandwidths = [1, 5, 5, 5]
    losses = [0, 0, 0, 0]  # 0% must be int

    mytopo = MyTopo(nodeNum,linkSet,bandwidths,losses)

    # CONTROLLER_IP = "127.0.0.1"  # Your ryu controller server IP
    # CONTROLLER_PORT = 5001
    OVSSwitch13 = partial(OVSSwitch, protocols='OpenFlow13')
    net = Mininet(topo=mytopo, switch=OVSSwitch13, link=TCLink, controller=None)
    net.addController('controller', controller=RemoteController)
    net.start()
    # h1,h2= net.get('h1','h2')
    # net.iperf((h1,h2))

    eps = 0
    port = 9000
    while(eps < 100):
        src,dst = linkSet[eps%len(linkSet)]

        delay, throughput, loss, popens = generate_request(net,src, port,dst,
                                                           port, 0, 1000,
                                                           1000000, eps)  # rtime is a deprecated para
        print delay,throughput,loss, popens
        port += 1
        eps += 1

    CLI(net)
    net.stop()