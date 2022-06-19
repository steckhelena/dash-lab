import json
import os
import sys
import time
from collections import OrderedDict
from multiprocessing import Process

from mininet.log import info, setLogLevel
from mininet.net import Mininet

station = []


def topology():

    mod = str(sys.argv[1])  # network type
    print("-------------------------------")
    print("Network Trace Type : " + str(mod) + "\n")

    nett = str(sys.argv[2])  # mobility
    print("-------------------------------")
    print("Network Trace Mobility : " + str(nett) + "\n")

    host = int(sys.argv[3])  # num of host
    print("-------------------------------")
    print("Number of Total Host : " + str(host) + "\n")

    algo = str(sys.argv[4])  # name of adaptation algorithm
    print("-------------------------------")
    print("ABS Algorithm : " + str(algo) + "\n")

    prot = str(sys.argv[5])  # name of protocol
    print("-------------------------------")
    print("Protocol : " + str(prot) + "\n")

    sertype = str(sys.argv[6])  # name of server
    print("-------------------------------")
    print("Server : " + str(sertype) + "\n")
    fol = int(sys.argv[7])  # num of host

    # Create a network
    net = Mininet()

    info("*** Creating nodes\n")
    for i in range(host):
        m = "sta%s" % (i + 1)
        j = i + 1
        station.insert(i, net.addHost(m, ip="10.0.0.2%s/24" % (j)))

    server = net.addHost("server", ip="10.0.0.1/24")

    dc = net.addHost("dc", ip="10.0.0.80/24")
    ds = net.addHost("ds", ip="10.0.0.81/24")

    s2 = net.addSwitch("s2")
    s1 = net.addSwitch("s1")

    c0 = net.addController("c0")

    info("*** Configuring wifi nodes\n")

    info("*** Associating Stations\n")
    for i in range(host):
        m = "sta%s" % (i + 1)
        net.addLink(m, s1)

    net.addLink(
        s2, s1, 1, 10, bw=100
    )  # initial link parameter default according to mininet

    net.addLink(server, s2, bw=1000)

    net.addLink(dc, s1)
    net.addLink(ds, s2)

    info("*** Starting network\n")
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])

    time.sleep(5)
    print("\n ")
    folder = (
        "fol_"
        + str(fol)
        + "_mode_"
        + (mod)
        + "_trace_"
        + str(nett)
        + "_host_"
        + str(host)
        + "_algo_"
        + str(algo)
        + "_protocol_"
        + str(prot)
        + "_server_"
        + str(sertype)
    )

    os.system("mkdir -p /home/raza/Downloads/goDASH/godash/data/" + folder)

    with open("/home/raza/Downloads/goDASHbed/config/configure.json") as json_file:
        test_dict = json.load(json_file, object_pairs_hook=OrderedDict)

    test_dict["adapt"] = algo

    if prot == "tcp":
        test_dict["quic"] = "off"
        test_dict["url"] = "https://www.godashbed.org/full/bbb_enc_x264_dash.mpd"
    else:
        test_dict["quic"] = "on"
        test_dict["url"] = "https://www.godashbed.org:4444/full/bbb_enc_x264_dash.mpd"

    test_dict["serveraddr"] = "off"

    json.dump(
        test_dict, open("/home/raza/Downloads/goDASH/godash/config/configure.json", "w")
    )

    st = []
    for i in range(host):
        m1 = "sta%s" % (i + 1)
        m2 = net[m1]
        st.insert(i, m2)

    switch2 = net["s2"]
    server = net["server"]
    # ap= net['ap1']
    switch1 = net["s1"]
    dc = net["dc"]
    ds = net["ds"]

    if mod == "3g":
        bt = 3
    elif mod == "4g":
        bt = 4
    else:
        bt = 5

    return (
        st,
        switch2,
        server,
        switch1,
        host,
        algo,
        nett,
        mod,
        prot,
        dc,
        ds,
        sertype,
        fol,
        bt,
    )


# server settings


def server(sr, prot, sertype):

    if sertype == "WSGI":
        if prot == "quic":
            sr.cmd(
                "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && caddy start --config ./caddy-config/TestbedTCP/CaddyFilev2QUIC --adapter caddyfile"
            )
            print("......WSGI(caddy) server and quic protocol.....")
        else:
            sr.cmd(
                "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && caddy start --config ./caddy-config/TestbedTCP/CaddyFilev2TCP --adapter caddyfile"
            )
            print("......WSGI(caddy) server  and tcp protocol.....")

    elif sertype == "ASGI":
        if prot == "quic":
            print(
                sr.cmd(
                    "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service &&  hypercorn hypercorn_goDASHbed_quic:app &"
                )
            )
            print("......ASGI(hypercorn) server and quic protocol.....")
        else:
            print(
                sr.cmd(
                    "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && hypercorn hypercorn_goDASHbed:app &"
                )
            )
            print("......ASGI(hypercorn) server and tcp protocol.....")


# pcap capture
def pcap(mod, host, algo, nett, prot, sertype, fol):
    print("Pcap capturing s1-eth10 ..........\n")
    # i coment, bcz it collect pcap of 1st client, will uncomment later if need to collect pcap
    os.system(
        "sudo tcpdump -i s1-eth10 -U -w  /home/raza/Downloads/goDASH/godash/data/fol_"
        + str(fol)
        + "_mode_"
        + (mod)
        + "_trace_"
        + str(nett)
        + "_host_"
        + str(host)
        + "_algo_"
        + str(algo)
        + "_protocol_"
        + str(prot)
        + "_server_"
        + str(sertype)
        + "/h1_ap.pcap"
    )


# tc script and kill process


def netcon(mod, nett, host):
    print(str(mod) + "-" + str(nett) + "  traces.............\n")
    os.system("sudo ./topo.sh %s %s" % (mod, nett))


# tc script
# def kp():

# os.system('sudo ./killprocess.sh &')

# run godash player


def player(mod, client, host, algo, nett, prot, sertype, fol):

    client.cmd(
        "cd /home/raza/Downloads/goDASH/godash && ./godash -config ./config/configure.json >/home/raza/Downloads/goDASH/godash/data/fol_"
        + str(fol)
        + "_mode_"
        + (mod)
        + "_trace_"
        + str(nett)
        + "_host_"
        + str(host)
        + "_algo_"
        + str(algo)
        + "_protocol_"
        + str(prot)
        + "_server_"
        + str(sertype)
        + "/h_"
        + str(client)
        + ".txt && echo ....Streaming done_"
        + str(client)
    )


def ditgr(s):
    print(s.cmd("cd /home/raza/D-ITG-2.8.1-r1023/bin  && ./ITGRecv"))


def ditgs(c, bt):
    print(
        c.cmd(
            "cd /home/raza/D-ITG-2.8.1-r1023/bin && ./ITGSend script_file1"
            + str(bt)
            + " -l sender.log -x receiver.log"
        )
    )


if __name__ == "__main__":
    setLogLevel("info")

    # station, switch, ser, ap, host, algo, nett, doc, num, mod, prot, dc, ds =  topology()
    (
        station,
        switch,
        ser,
        ap,
        host,
        algo,
        nett,
        mod,
        prot,
        dc,
        ds,
        st,
        fol,
        bt,
    ) = topology()
    # CLI(net)
    a = True
    b = False
    c = False
    d = False
    e = False
    f = False
    g = False
    h = False

    if a:
        n = Process(target=pcap, args=(mod, host, algo, nett, prot, st, fol))
        n.start()
        d = True

    if d:
        y = Process(
            target=server,
            args=(
                ser,
                prot,
                st,
            ),
        )
        y.start()
        e = True

    if e:
        nn = Process(
            target=netcon,
            args=(
                mod,
                nett,
                host,
            ),
        )
        nn.start()
        f = True
    if f:
        for k in range(host):
            print("Start streaming......")
            q = Process(
                target=player,
                args=(
                    mod,
                    station[k],
                    host,
                    algo,
                    nett,
                    prot,
                    st,
                    fol,
                ),
            )
            q.start()
            q.join
