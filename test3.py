import json
import os
import pathlib
from collections import OrderedDict
from multiprocessing import Process
from typing import List, Literal, TypedDict, Union

from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import Host, Switch

MobilityType = Union[
    Literal["Driving-1"],
    Literal["Driving-10"],
    Literal["Driving-2"],
    Literal["Driving-6"],
    Literal["Driving-7"],
    Literal["Driving-8"],
    Literal["Driving-9"],
    Literal["Static-1"],
    Literal["Static-2"],
    Literal["Static-3"],
]


class Experiment(TypedDict):
    id: int
    mode: Literal["5g"]
    mobility: MobilityType
    clients: int
    server_type: Union[Literal["asgi"], Literal["wsgi"]]
    adaptation_algorithm: Union[
        Literal["conventional"], Literal["elastic"], Literal["bba"], Literal["logistic"]
    ]
    server_protocol: Union[Literal["quic"], Literal["tcp"]]
    godash_config_path: str
    godash_bin_path: str


class TopologyResponse(TypedDict):
    stations: List[Host]
    switch1: Switch
    switch2: Switch
    server: Host


def topology(experiment: Experiment) -> TopologyResponse:
    """
    This function is responsible for setting up the mininet topology for the dash
    lab tests.

    The topology is as follows:
    ┌────────┐
    │Client 1├───┐
    └────────┘   │
        .        │
        .        │ ┌────────┐       ┌────────┐     ┌──────┐
        .  ──────┼─┤Swith s1├───────┤Swith s2├─────┤Server│
        .        │ └────────┘       └────────┘     └──────┘
        .        │
    ┌────────┐   │
    │Client N├───┘
    └────────┘
    """

    # Create a network
    net = Mininet()

    stations = []

    info("*** Creating nodes\n")
    for i in range(experiment["clients"]):
        m = "sta%s" % (i + 1)
        j = i + 1
        stations.insert(i, net.addHost(m, ip="10.0.0.2%s/24" % (j)))

    server = net.addHost("server", ip="10.0.0.1/24")

    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")

    controller = net.addController("c0")

    info("*** Configuring wifi nodes\n")

    info("*** Associating Stations\n")
    for i in range(experiment["clients"]):
        m = "sta%s" % (i + 1)
        net.addLink(m, switch1)

    net.addLink(switch2, switch1, 1, 10)
    net.addLink(server, switch2)

    info("*** Starting network\n")
    net.build()
    controller.start()
    switch2.start([controller])
    switch1.start([controller])

    net.waitConnected()

    switch2 = net["s2"]
    server = net["server"]
    switch1 = net["s1"]

    return {
        "stations": stations,
        "switch2": switch2,
        "switch1": switch2,
        "server": server,
    }


def load_experiment_config(experiment: Experiment):
    with open(experiment["godash_config_path"]) as json_file:
        test_dict = json.load(json_file, object_pairs_hook=OrderedDict)

    test_dict["adapt"] = experiment["adaptation_algorithm"]

    if experiment["server_protocol"] == "tcp":
        test_dict["quic"] = "off"
        test_dict["url"] = "https://www.godashbed.org/full/bbb_enc_x264_dash.mpd"
    else:
        test_dict["quic"] = "on"
        test_dict["url"] = "https://www.godashbed.org:4444/full/bbb_enc_x264_dash.mpd"

    test_dict["serveraddr"] = "off"

    json.dump(test_dict, open(experiment["godash_config_path"], "w"))


def print_experiment(experiment: Experiment):
    print("-------------------------------")
    print(f"Network Trace Type : {experiment['server_type']}\n")

    print("-------------------------------")
    print(f"Network Trace Mobility : {experiment['mobility']}\n")

    print("-------------------------------")
    print(f"Number of clients: {experiment['clients']}\n")

    print("-------------------------------")
    print(f"ABS Algorithm : {experiment['adaptation_algorithm']}\n")

    print("-------------------------------")
    print(f"Protocol : {experiment['server_protocol']}\n")


def get_experiment_folder_name(experiment: Experiment) -> str:
    experiment_folder = (
        f"id_{experiment['id']}_mode_{experiment['mode']}_trace_"
        + f"{experiment['mobility']}_host_{experiment['clients']}_algo_"
        + f"{experiment['adaptation_algorithm']}_protocol_"
        + f"{experiment['server_protocol']}_server_{experiment['server_type']}"
    )
    absolute_experiment_folder = os.path.join(os.getcwd(), experiment_folder)

    # create folder if not exists
    pathlib.Path(absolute_experiment_folder).mkdir(parents=True, exist_ok=True)

    return absolute_experiment_folder


def get_client_output_file_name(experiment: Experiment, client) -> str:
    return os.path.join(get_experiment_folder_name(experiment), str(client))


# server settings


def server(server: Host, experiment: Experiment):
    if experiment["server_type"] == "wsgi":
        if experiment["server_protocol"] == "quic":
            server.cmd(
                "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && caddy start --config ./caddy-config/TestbedTCP/CaddyFilev2QUIC --adapter caddyfile"
            )
            print("......WSGI(caddy) server and quic protocol.....")
        else:
            server.cmd(
                "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && caddy start --config ./caddy-config/TestbedTCP/CaddyFilev2TCP --adapter caddyfile"
            )
            print("......WSGI(caddy) server  and tcp protocol.....")

    elif experiment["server_type"] == "asgi":
        if experiment["server_protocol"] == "quic":
            print(
                server.cmd(
                    "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service &&  hypercorn hypercorn_goDASHbed_quic:app &"
                )
            )
            print("......ASGI(hypercorn) server and quic protocol.....")
        else:
            print(
                server.cmd(
                    "cd /home/raza/Downloads/goDASHbed && sudo systemctl stop apache2.service && hypercorn hypercorn_goDASHbed:app &"
                )
            )
            print("......ASGI(hypercorn) server and tcp protocol.....")


def pcap(experiment: Experiment):
    print("Pcap capturing s1-eth10 ..........\n")
    os.system(f"tcpdump -i s1-eth10 -U -w {get_experiment_folder_name(experiment)}")


def tc(experiment: Experiment, client: Host):
    os.system("./topo.sh %s %s" % (experiment["mobility"], client.name))


def player(experiment: Experiment, client: Host):
    client.cmd(
        f"{experiment['godash_bin_path']} -config"
        + f"{experiment['godash_config_path']}"
        + f"> {get_client_output_file_name(experiment, client)}.txt "
        + f"&& echo ....Streaming done_{client}"
    )


if __name__ == "__main__":
    setLogLevel("info")

    experiment: Experiment = {
        "mobility": "Driving-8",
        "server_type": "wsgi",
        "server_protocol": "tcp",
        "clients": 1,
        "mode": "5g",
        "id": 1,
        "adaptation_algorithm": "bba",
        "godash_config_path": "/home/raza/Downloads/goDASHbed/config/configure.json",
        "godash_bin_path": "/home/raza/Downloads/goDASH/godash/godash",
    }

    # station, switch, ser, ap, host, algo, nett, doc, num, mod, prot, dc, ds =  topology()
    topology_response = topology(experiment)

    # Start pcap on switch 1
    pcap_process = Process(target=pcap, args=(experiment))
    pcap_process.start()

    # Start server
    server_process = Process(
        target=server,
        args=(topology_response["server"], experiment),
    )
    server_process.start()

    # Start streaming for each client station
    for host in topology_response["stations"]:
        # Start traffic control for node
        tc_process = Process(
            target=tc,
            args=(experiment, host),
        )
        tc_process.start()

        # Start streaming on node
        print("Start streaming......")
        player_process = Process(
            target=player,
            args=(experiment, host),
        )
        player_process.start()
        player_process.join()
