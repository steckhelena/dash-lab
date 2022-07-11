import json
import os
import pathlib
import subprocess
from collections import OrderedDict
from multiprocessing import Process
from time import sleep
from typing import Literal, TypedDict, Union

from mininet.clean import cleanup
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import Host, Switch

from normalize_datasets import NormalizedDataset, get_normalized_datasets


class Experiment(TypedDict):
    id: int
    mode: Literal["5g"]
    mobility: NormalizedDataset
    server_type: Union[Literal["asgi"], Literal["wsgi"]]
    adaptation_algorithm: Union[
        Literal["conventional"], Literal["elastic"], Literal["bba"], Literal["logistic"]
    ]
    server_protocol: Union[Literal["quic"], Literal["tcp"]]
    godash_config_path: str
    godash_bin_path: str


class ExperimentResult(TypedDict):
    experiment: Experiment
    experiment_godash_result_path: str
    experiment_host_pcap_path: str
    had_to_restart_tc: bool


class TopologyResponse(TypedDict):
    client: Host
    switch1: Switch
    server: Host


def topology() -> TopologyResponse:
    """
    This function is responsible for setting up the mininet topology for the dash
    lab tests.

    The topology is as follows:
    ┌────────┐     ┌────────┐    ┌──────┐
    │Client 1├─────┤Swith s1├────┤Server│
    └────────┘     └────────┘    └──────┘
    """

    # Create a network
    cleanup()
    net = Mininet()

    info("*** Creating node\n")
    client = net.addHost("sta1", ip="10.0.0.21/24")
    server = net.addHost("server", ip="10.0.0.1/24")
    switch1 = net.addSwitch("s1")
    controller = net.addController("c0")

    info("*** Configuring wifi nodes\n")

    info("*** Associating Stations\n")
    net.addLink(client, switch1)
    net.addLink(server, switch1)

    info("*** Starting network\n")
    net.build()
    controller.start()
    switch1.start([controller])

    net.waitConnected()

    server = net["server"]
    switch1 = net["s1"]

    return {
        "client": client,
        "switch1": switch1,
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
    print(f"Network Trace Mobility : {experiment['mobility']['name']}\n")

    print("-------------------------------")
    print(f"ABS Algorithm : {experiment['adaptation_algorithm']}\n")

    print("-------------------------------")
    print(f"Protocol : {experiment['server_protocol']}\n")


def get_experiment_folder_name(experiment: Experiment) -> str:
    experiment_folder = (
        "experiment_results/"
        + f"id_{experiment['id']}_mode_{experiment['mode']}_trace_"
        + f"{experiment['mobility']['name']}_algo_"
        + f"{experiment['adaptation_algorithm']}_protocol_"
        + f"{experiment['server_protocol']}_server_{experiment['server_type']}"
    )
    absolute_experiment_folder = os.path.join(os.getcwd(), experiment_folder)

    # create folder if not exists
    pathlib.Path(absolute_experiment_folder).mkdir(parents=True, exist_ok=True)

    return absolute_experiment_folder


def get_client_output_file_name(experiment: Experiment, client: Host) -> str:
    return os.path.join(get_experiment_folder_name(experiment), str(client))


def get_pcap_output_file_name(experiment: Experiment, client: Host) -> str:
    return os.path.join(get_experiment_folder_name(experiment), f"{client.intf()}.pcap")


# server settings


def server(server: Host, experiment: Experiment):
    load_experiment_config(experiment)

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


def pcap(experiment: Experiment, client: Host):
    print(f"Pcap capturing {client.intf()} ..........\n")
    send_cmd(
        client,
        f"tcpdump -i {client.intf()} -U -w"
        + f" {get_pcap_output_file_name(experiment, client)}",
    )


def send_cmd(client: Host, cmd: str):
    proc = client.popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    try:
        out, err = proc.communicate()

        if proc.returncode != 0:
            raise Exception(f"Error for command: {cmd}", err)

        return out, err
    finally:
        proc.kill()


def tc(experiment: Experiment, client: Host):
    intf = client.intf()
    initial_data = experiment["mobility"]["data"][0]
    initial_download_speed = initial_data["download_kbps"]
    initial_upload_speed = initial_data["upload_kbps"]
    initial_interval = initial_data["change_interval_seconds"]

    print(f"Setting initial data for {initial_interval}s:")
    print(f"Download speed: {initial_download_speed}kbps")
    print(f"Upload speed: {initial_upload_speed}kbps")

    # create root upload interface
    send_cmd(client, f"tc qdisc add dev {intf} root handle 1: htb default 1")

    # create initial upload class
    send_cmd(
        client,
        f"tc class add dev {intf} parent 1: classid 1:1 htb rate {initial_upload_speed}kbps",
    )

    # create ifb interface to control ingress traffic
    send_cmd(
        client,
        "modprobe ifb && ip link add name ifb0 type ifb && ip link set dev ifb0 up",
    )
    send_cmd(
        client,
        "tc qdisc add dev ifb0 root handle 2: htb r2q 1"
        + f" && tc class add dev ifb0 parent 2: classid 2:2 htb rate {initial_download_speed}kbps"
        + " && tc filter add dev ifb0 parent 2: matchall flowid 2:2",
    )
    send_cmd(
        client,
        f"tc qdisc add dev {intf} ingress"
        + f" && tc filter add dev {intf} ingress matchall action mirred egress redirect dev ifb0",
    )

    # sleep before changing values
    sleep(initial_interval)

    failed_processes = 0
    for current_data in experiment["mobility"]["data"][1:]:
        curr_download_speed = current_data["download_kbps"]
        curr_upload_speed = current_data["upload_kbps"]
        curr_interval = current_data["change_interval_seconds"]

        print(f"Setting data for {curr_interval}s:")
        print(f"Download speed: {curr_download_speed}kbps")
        print(f"Upload speed: {curr_upload_speed}kbps")

        # change download class rate
        send_cmd(
            client,
            f"tc class change dev ifb0 parent 2: classid 2:2 htb rate {curr_download_speed}kbps",
        )
        # change upload class rate
        send_cmd(
            client,
            f"tc class change dev {intf} parent 1: classid 1:1 htb rate {curr_upload_speed}kbps",
        )

        # sleep before changing rate again
        sleep(curr_interval)

        # check if process stopped
        num_processes, _ = send_cmd(client, "ps -ef | grep godash | wc -l")
        print(f"Number of godash processes: {int(num_processes)}")

        if int(num_processes) <= 2:
            failed_processes += 1
        else:
            failed_processes = 0

        if failed_processes > 3:
            print("No godash process running, stopping traffic control")
            break

    # Cleanup TC on end
    send_cmd(client, f"tc qdisc del dev {intf} ingress && tc qdisc del dev ifb0 root")
    send_cmd(client, f"tc qdisc del dev {intf} root")


def player(experiment: Experiment, client: Host):
    cmd = (
        f"{experiment['godash_bin_path']} -config "
        + f"{experiment['godash_config_path']} "
        + f"> {get_client_output_file_name(experiment, client)}.txt"
    )
    print(cmd)
    print(client.cmd(cmd))


def run_experiment(experiment: Experiment) -> ExperimentResult:
    # build topology for experiment
    topology_response = topology()

    # Start pcap on client
    pcap_process = Process(target=pcap, args=(experiment, topology_response["client"]))
    pcap_process.start()

    # Start server
    server_process = Process(
        target=server,
        args=(topology_response["server"], experiment),
    )
    server_process.start()

    # Start traffic control for node
    tc_process = Process(
        target=tc,
        args=(experiment, topology_response["client"]),
    )
    tc_process.start()
    had_to_restart_tc = False

    # Start streaming on node
    print("Start streaming......")
    player_process = Process(
        target=player,
        args=(experiment, topology_response["client"]),
    )
    player_process.start()
    tc_process.join()

    # If player did not stop streaming, restart TC
    while player_process.is_alive():
        had_to_restart_tc = True
        tc_process = Process(
            target=tc,
            args=(experiment, topology_response["client"]),
        )
        tc_process.start()
        tc_process.join()

    player_process.join()
    print("Streaming done......")

    print("Stopping pcap capturing......")
    pcap_process.kill()

    print("Stopping server......")
    server_process.kill()

    return {
        "experiment": experiment,
        "experiment_godash_result_path": get_client_output_file_name(
            experiment, topology_response["client"]
        ),
        "experiment_host_pcap_path": get_pcap_output_file_name(
            experiment, topology_response["client"]
        ),
        "had_to_restart_tc": had_to_restart_tc,
    }


if __name__ == "__main__":
    setLogLevel("info")

    normalized_datasets = get_normalized_datasets()

    experiment: Experiment = {
        "mobility": normalized_datasets[0],
        "server_type": "wsgi",
        "server_protocol": "tcp",
        "mode": "5g",
        "id": 2,
        "adaptation_algorithm": "bba",
        "godash_config_path": "/home/raza/Downloads/goDASHbed/config/configure.json",
        "godash_bin_path": "/home/raza/Downloads/goDASH/godash/godash",
    }

    print(run_experiment(experiment))
