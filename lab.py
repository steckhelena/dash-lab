import argparse
import json
import os
import pathlib
import subprocess
import tempfile
import time
from collections import OrderedDict
from multiprocessing import Process, Value
from time import sleep
from typing import Literal, TypedDict, Union

import numpy as np
from mininet.clean import cleanup
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import Host, Switch

from datasets5G import datasets5G
from fill_templates import fill_template
from normalize_datasets import NormalizedDataset, get_normalized_datasets
from process_results import cleanup_pcap, process_pcap

verbose = False


class Formatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


class Experiment(TypedDict):
    id: int
    repetition: int
    mode: str
    mobility: NormalizedDataset
    server_type: Union[Literal["asgi"], Literal["wsgi"]]
    adaptation_algorithm: Union[
        Literal["conventional"], Literal["elastic"], Literal["bba"], Literal["logistic"]
    ]
    server_protocol: Union[Literal["quic"], Literal["tcp"]]
    godash_config_path: str
    godash_bin_path: str
    experiment_root_path: str
    mpd_path: str


class ExperimentResult(TypedDict):
    experiment: Experiment
    server_ip: str
    experiment_folder: str
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
        test_dict["url"] = f"https://www.godashbed.org/{experiment['mpd_path']}"
    else:
        test_dict["quic"] = "on"
        test_dict["url"] = f"https://www.godashbed.org:4444/{experiment['mpd_path']}"

    test_dict["serveraddr"] = "off"

    json.dump(test_dict, open(get_godash_config_temp_path(), "w"))


def print_experiment(experiment: Experiment):
    print("=" * 10)
    print("Starting experiment for: ")
    print(f"Dataset: {experiment['mobility']['name']}")
    print(f"Server type: {experiment['server_type']}")
    print(f"Server protocol: {experiment['server_protocol']}")
    print(f"Adaptation algorithm: {experiment['adaptation_algorithm']}")
    print(f"Server mpd: {experiment['mpd_path']}")
    print("=" * 10)


def get_godash_config_temp_path() -> str:
    return (pathlib.Path(tempfile.gettempdir()) / "dash-lab-configure.json").as_posix()


def get_experiment_root_folder(experiment: Experiment) -> str:
    experiment_folder = experiment["experiment_root_path"]
    absolute_experiment_folder = os.path.abspath(experiment_folder)

    # create folder if not exists
    pathlib.Path(absolute_experiment_folder).mkdir(parents=True, exist_ok=True)

    return absolute_experiment_folder


def get_experiment_folder_name(experiment: Experiment) -> str:
    experiment_folder = os.path.join(
        get_experiment_root_folder(experiment),
        f"{experiment['mode']}/"
        + f"{experiment['mobility']['name']}/"
        + f"{experiment['mpd_path'].split('/')[3]}/"
        + f"{experiment['mpd_path'].split('/')[1]}/"
        + f"{experiment['adaptation_algorithm']}/"
        + f"{experiment['server_protocol']}/{experiment['server_type']}/"
        + f"id_{experiment['id']}",
    )
    absolute_experiment_folder = os.path.abspath(experiment_folder)

    # create folder if not exists
    pathlib.Path(absolute_experiment_folder).mkdir(parents=True, exist_ok=True)

    return absolute_experiment_folder


def get_client_output_file_name(experiment: Experiment, client: Host) -> str:
    return os.path.join(get_experiment_folder_name(experiment), f"{client}.txt")


def get_pcap_output_file_name(experiment: Experiment, client: Host) -> str:
    return os.path.join(get_experiment_folder_name(experiment), f"{client.intf()}.pcap")


def get_experiment_result_file_name(experiment: ExperimentResult) -> str:
    return os.path.join(experiment["experiment"]["experiment_root_path"], "result.json")


def get_experiment_checkpoint_file_name(experiment_root_folder: str) -> str:
    return os.path.join(experiment_root_folder, "checkpoint.txt")


def get_defaults_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent.absolute() / "godash_defaults"


# server settings
def server(server: Host, experiment: Experiment):
    load_experiment_config(experiment)
    parent_dir = get_defaults_path()

    print(
        f"sudo systemctl stop apache2.service && caddy start --config {parent_dir / 'CaddyFilev2QUIC'} --adapter caddyfile"
    )
    if experiment["server_type"] == "wsgi":
        if experiment["server_protocol"] == "quic":
            server.cmd(
                f"sudo systemctl stop apache2.service && caddy start --config {parent_dir / 'CaddyFilev2QUIC'} --adapter caddyfile"
            )
            print("......WSGI(caddy) server and quic protocol.....")
        else:
            server.cmd(
                f"sudo systemctl stop apache2.service && caddy start --config {parent_dir / 'CaddyFilev2TCP'} --adapter caddyfile"
            )
            print("......WSGI(caddy) server  and tcp protocol.....")

    elif experiment["server_type"] == "asgi":
        if experiment["server_protocol"] == "quic":
            print(
                server.cmd(
                    f"sudo systemctl stop apache2.service &&  hypercorn {parent_dir / 'hypercorn_goDASHbed_quic'}:app &"
                )
            )
            print("......ASGI(hypercorn) server and quic protocol.....")
        else:
            print(
                server.cmd(
                    f"sudo systemctl stop apache2.service && hypercorn {parent_dir / 'hypercorn_goDASHbed'}:app &"
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


def tc(experiment: Experiment, client: Host, is_finished):
    intf = client.intf()
    initial_data = experiment["mobility"]["data"][0]
    initial_download_speed = initial_data["download_kbps"]
    initial_upload_speed = initial_data["upload_kbps"]
    initial_interval = initial_data["change_interval_seconds"]

    if verbose:
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

    for current_data in experiment["mobility"]["data"][1:]:
        curr_download_speed = current_data["download_kbps"]
        curr_upload_speed = current_data["upload_kbps"]
        curr_interval = current_data["change_interval_seconds"]

        if verbose:
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
        if is_finished.value == True:
            print("No godash process running, stopping traffic control")
            break

    # Cleanup TC on end
    send_cmd(client, f"tc qdisc del dev {intf} ingress && tc qdisc del dev ifb0 root")
    send_cmd(client, f"tc qdisc del dev {intf} root")


def player(experiment: Experiment, client: Host, is_finished):
    cmd = (
        f"{experiment['godash_bin_path']} -config "
        + f"{get_godash_config_temp_path()} "
        + f"> {get_client_output_file_name(experiment, client)}"
    )
    print(cmd)
    print(client.cmd(cmd))
    is_finished.value = True


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
    is_finished_streaming = Value("i", False)
    tc_process = Process(
        target=tc,
        args=(experiment, topology_response["client"], is_finished_streaming),
    )
    tc_process.start()
    had_to_restart_tc = False

    # Start streaming on node
    print("Start streaming......")
    player_process = Process(
        target=player,
        args=(experiment, topology_response["client"], is_finished_streaming),
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
        "server_ip": topology_response["server"].IP(),
        "experiment_godash_result_path": get_client_output_file_name(
            experiment, topology_response["client"]
        ),
        "experiment_host_pcap_path": get_pcap_output_file_name(
            experiment, topology_response["client"]
        ),
        "experiment_folder": get_experiment_folder_name(experiment),
        "had_to_restart_tc": had_to_restart_tc,
    }


def get_experiment_ordered_hash(experiment: Experiment):
    return (
        f"{experiment['mobility']['name']}"
        + f"{experiment['mpd_path']}"
        + f"{experiment['mode']}"
        + f"{experiment['adaptation_algorithm']}"
        + f"{experiment['server_protocol']}"
        + f"{experiment['server_type']}"
        + f"{experiment['repetition']}"
    )


def parse_command_line_options():
    parser = argparse.ArgumentParser(
        description="""
        This is a command line utility to run a simulated environment for DASH
        video streaming tests. It uses goDASHbed for running the server and
        godash for running DASH clients to consume the content and generate QoE
        features for the video result.

        This environment supports simulating network conditions based on network
        traces.

        The traces should be in a format similar to those provided by the
        `Beyond Throughput, The Next Generation: a 5G Dataset with Channel and
        Context Metrics`[1] work.

        This CLI will create, for each experiment run, one host node for
        receiving the streamed content using goDASH[2][3], one server node for
        streaming DASH files using goDASHbed[2][3] and one switch connecting
        both of them. To do this it uses mininet[4], the network topology is as
        follows:
        ┌────────┐     ┌────────┐    ┌──────┐
        │Client 1├─────┤Swith s1├────┤Server│
        └────────┘     └────────┘    └──────┘

        The network simulation is done using the tc linux tool which offers
        traffic control for the Linux Kernel. To do this we use traffic shaping
        in order to limit the bandwidth available for both download and upload
        traffic. This is done on the client node interface.

        For the traffic shaping to work properly on the download bandwidth the
        ifb kernel module needs to be loaded. To check if it is use:
        `lsmod | grep ifb`, if this has no output then it isn't, to load it run
        `sudo modprobe ifb`. This module is used as pseudo network interface as
        a concentrator for all traffic incoming on the client network interface,
        then we can apply traffic shaping on that traffic by using tc qdiscs
        when we otherwise would not be able to.

        This command line interface is based on a previous work `DASH QoE
        Performance Evaluation Framework with 5G Datasets`[5] and builds upon
        it.

        [1] D. Raca, D. Leahy, C.J. Sreenan and J.J. Quinlan. Beyond Throughput,
        The Next Generation: A 5G Dataset with Channel and Context Metrics. ACM
        Multimedia Systems Conference (MMSys), Istanbul, Turkey. June 8-11, 2020
        [2] D. Raca, M. Manifacier, and J.J. Quinlan. goDASH - GO accelerated
        HAS framework for rapid prototyping. 12th International Conference on
        Quality of Multimedia Experience (QoMEX), Athlone, Ireland. 26th to 28th
        May, 2020 CORA
        [3] John O’Sullivan, D. Raca, and Jason J. Quinlan. Demo Paper: godash
        2.0 - The Next Evolution of HAS Evaluation. 21st IEEE International
        Symposium On A World Of Wireless, Mobile And Multimedia Networks (IEEE
        WoWMoM 2020), Cork, Ireland. August 31 to September 03, 2020 CORA
        [4] https://github.com/mininet/mininet
        [5] R. Ul Mustafa, M. T. Islam, C. Rothenberg, S. Ferlin, D. Raca and J.
        J. Quinlan, "DASH QoE Performance Evaluation Framework with 5G
        Datasets," 2020 16th International Conference on Network and Service
        Management (CNSM), Izmir, Turkey, 2020, pp. 1-6, doi:
        10.23919/CNSM50824.2020.9269111.
        """,
        formatter_class=Formatter,
    )

    parser.add_argument(
        "--godash-bin",
        help="<Required> Path to goDASH executable.",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--godash-config-template",
        default=(get_defaults_path() / "configure.json").as_posix(),
        help="""Path to goDASH configuration template. This will be the base for
        the goDASH configuration, the fields 'quic', 'url' 'serveraddr' and
        'adapt' will be overwritten for the running experiment. The other fields
        will stay the same.""",
        type=str,
    )

    parser.add_argument(
        "-m",
        "--mpd-path",
        action="append",
        help="""<Required> Path from the server root to the mpd files with
        information on the DASH videos to be streamed. Can be added multiple
        times. E.g.: `-m a/b.mpd -m b/c.mpd`""",
        required=True,
    )

    parser.add_argument(
        "--dash-files-root",
        default="/var/www/html",
        help="""This is the root to the DASH files to be served by the file
        server, i.e. the path where the DASH segments are stored, the mpd paths
        are relative to this.""",
    )

    parser.add_argument(
        "-d",
        "--dataset",
        action="append",
        help="""System path, relative or absolute, to the dataset
        which will be used to simulate the network conditions, can be added
        multiple times, requires one -t/--dataset-type set for each. E.g.:
        `-d a/b.csv -t4g -d b/c.csv -t5g`. If not provided defaults to the
        datasets from [1].""",
    )

    parser.add_argument(
        "-t",
        "--dataset-type",
        action="append",
        help="""Type of the dataset. E.g.: 5g, 4g, 3g.""",
    )

    parser.add_argument(
        "-r",
        "--repetitions",
        type=int,
        default=5,
        help="""Number of repetitions for each experiment combination.""",
    )

    parser.add_argument(
        "--algos",
        nargs="+",
        default=["bba", "conventional", "elastic", "logistic"],
        choices=["bba", "conventional", "elastic", "logistic"],
        help="""What algorithms to run the experiments with.""",
    )

    parser.add_argument(
        "--protocols",
        nargs="+",
        default=["tcp", "quic"],
        choices=["tcp", "quic"],
        help="""What protocols to run the experiments with.""",
    )

    parser.add_argument(
        "--types",
        nargs="+",
        default=["wsgi", "asgi"],
        choices=["wsgi", "asgi"],
        help="""What kind of server gateway to run the experiments with.""",
    )

    parser.add_argument(
        "--experiment-root",
        type=str,
        default="experiment_results",
        help="""The experiment output folder path, can be relative or
        absolute.""",
    )

    parser.add_argument(
        "-c",
        "--use-checkpoint",
        action="store_true",
        help="""Use a checkpoint file for easily resuming experiments execution
        if stopped. Defaults to using a checkpoint.""",
    )
    parser.add_argument(
        "--no-use-checkpoint",
        action="store_false",
        dest="use_checkpoint",
        help="""Do not use a checkpoint file for easily resuming experiments
        execution if stopped. Defaults to using a checkpoint.""",
    )
    parser.set_defaults(use_checkpoint=True)

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="""Makes output verbose.""",
        default=False,
    )

    result = parser.parse_args()
    if not result.dataset and not result.dataset_type:
        result.dataset = datasets5G
        result.dataset_type = ["5g"] * len(datasets5G)

    if len(result.dataset) != len(result.dataset_type):
        raise Exception(
            "There needs to be the same number of dataset entries as there are dataset types!"
        )

    return result


if __name__ == "__main__":
    parsed_commands = parse_command_line_options()

    mpd_paths = parsed_commands.mpd_path
    datasets = parsed_commands.dataset
    dataset_modes = parsed_commands.dataset_type
    server_types = parsed_commands.types
    server_protocols = parsed_commands.protocols
    experiments_per_combination = parsed_commands.repetitions
    algos = parsed_commands.algos
    use_checkpoint = parsed_commands.use_checkpoint
    experiment_root = parsed_commands.experiment_root
    godash_bin_path = parsed_commands.godash_bin
    godash_config_path = parsed_commands.godash_config_template
    verbose = parsed_commands.verbose

    if verbose:
        setLogLevel("info")
    else:
        setLogLevel("warning")

    normalized_datasets = get_normalized_datasets(datasets)

    done_experiment_hashes = set()
    if use_checkpoint and os.path.exists(
        get_experiment_checkpoint_file_name(experiment_root)
    ):
        with open(get_experiment_checkpoint_file_name(experiment_root)) as f:
            done_experiment_hashes = set(f.read().splitlines())

    # fill server templates before starting out:
    fill_template(
        (get_defaults_path() / "CaddyFilev2QUIC.jinja").as_posix(),
        (get_defaults_path() / "CaddyFilev2QUIC").as_posix(),
        parsed_commands.dash_files_root,
        get_defaults_path().as_posix().rstrip("/"),
    )
    fill_template(
        (get_defaults_path() / "CaddyFilev2TCP.jinja").as_posix(),
        (get_defaults_path() / "CaddyFilev2TCP").as_posix(),
        parsed_commands.dash_files_root,
        get_defaults_path().as_posix().rstrip("/"),
    )
    fill_template(
        (get_defaults_path() / "hypercorn_goDASHbed.py.jinja").as_posix(),
        (get_defaults_path() / "hypercorn_goDASHbed.py").as_posix(),
        parsed_commands.dash_files_root,
        get_defaults_path().as_posix().rstrip("/"),
    )
    fill_template(
        (get_defaults_path() / "hypercorn_goDASHbed_quic.py.jinja").as_posix(),
        (get_defaults_path() / "hypercorn_goDASHbed_quic.py").as_posix(),
        parsed_commands.dash_files_root,
        get_defaults_path().as_posix().rstrip("/"),
    )

    for mpd_path in mpd_paths:
        for dataset, mode in zip(normalized_datasets, dataset_modes):
            for adaptation_algorithm in algos:
                for server_type in server_types:
                    for server_protocol in server_protocols:
                        for i in range(experiments_per_combination):
                            experiment: Experiment = {
                                "mobility": dataset,
                                "server_type": server_type,
                                "server_protocol": server_protocol,
                                "mode": mode,
                                "id": int(time.time()),
                                "repetition": i,
                                "adaptation_algorithm": adaptation_algorithm,
                                "godash_config_path": godash_config_path,
                                "godash_bin_path": godash_bin_path,
                                "mpd_path": mpd_path,
                                "experiment_root_path": experiment_root,
                            }  # type: ignore

                            experiment_ordered_hash = get_experiment_ordered_hash(
                                experiment
                            )
                            if (
                                use_checkpoint
                                and experiment_ordered_hash in done_experiment_hashes
                            ):
                                print(
                                    f"Skipping experiment with hash {experiment_ordered_hash} as it was already run"
                                )
                                continue

                            print_experiment(experiment)

                            experiment_result = run_experiment(experiment)

                            with open(
                                get_experiment_result_file_name(experiment_result), "w"
                            ) as f:
                                result = json.dumps(experiment_result, cls=NpEncoder)
                                f.write(result)

                            print("Processing pcap result")
                            process_pcap(experiment_result)

                            print("Removing processed pcap file")
                            cleanup_pcap(experiment_result)

                            if use_checkpoint:
                                print("Saving to checkpoint")
                                with open(
                                    get_experiment_checkpoint_file_name(
                                        experiment_root
                                    ),
                                    "a",
                                ) as f:
                                    f.write(f"{experiment_ordered_hash}\n")
                                    done_experiment_hashes.add(experiment_ordered_hash)
