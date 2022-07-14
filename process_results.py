import json
import os
import pathlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scapy.all import rdpcap
from scapy.layers.inet import IP, TCP, UDP

if TYPE_CHECKING:
    from lab import ExperimentResult


def Average(lst):
    if lst:
        return sum(lst) / len(lst)
    else:
        return 0


def get_godash_result_as_dataframe(godash_result_path: str) -> pd.DataFrame:
    with open(godash_result_path, "r+") as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines([line for line in lines if not re.match(r"^[0-9]+$", line)])
        f.truncate()

    return pd.read_csv(godash_result_path, delim_whitespace=True)  # type: ignore


def process_pcap_tcp(experiment_result: "ExperimentResult"):
    server_ip = experiment_result["server_ip"]

    pcap = rdpcap(experiment_result["experiment_host_pcap_path"])

    godash_result = get_godash_result_as_dataframe(
        experiment_result["experiment_godash_result_path"]
    )
    godash_timestamps = godash_result["Arr_time"]
    godash_timestamps_before = pd.concat(
        [pd.Series([0]), godash_timestamps[:-1]], ignore_index=True
    )
    godash_timestamps_after = godash_timestamps[0:]

    connection = set()
    for ppp in pcap:
        if ppp.haslayer(TCP) and ppp.haslayer(IP):
            if ppp[IP].dst == server_ip:
                if ppp[TCP].flags == "FA" or ppp[TCP].flags == "F":
                    connection.add(ppp[TCP].sport)

    df = pd.DataFrame(
        columns=[
            "Arr_time",
            "interIntervalTimeDP",
            "interIntervalTimeDP_GT100",
            "AvgTimeBWDPK",
            "AvgTimeBWDPK_GT100",
            "DThroughput",
            "DTTime",
            "DTotal_Packets",
            "DTotal_Packets_GT100",
            "STD_Less",
            "STD_GT",
            "DP_Times_str",
            "Packets_str",
            "GT100_Times_str",
            "GT100_Packets_str",
        ]
    )
    for beginning, end in zip(godash_timestamps_before, godash_timestamps_after):
        segment_time = (end - beginning) / 1000

        dl_05 = 0
        dc_05 = 0
        dc_gt100_05 = 0
        da_05 = 0
        dt_05 = 0
        packets_time_05 = []
        d_ia_05 = []
        d_pk_size_05 = []
        d_pk_size_gt100_05 = []
        ul_05 = 0
        uc_gt100_05 = 0
        ua_05 = 0
        ut_05 = 0
        uc_05 = 0
        u_ia_05 = []
        u_pk_size_05 = []
        u_pk_size_gt100_05 = []
        d_packets_gt_100_time = []
        u_packets_time_05 = []
        u_packets_gt_100_time = []

        for p in pcap:
            packet_elapsed_time = float(p.time - pcap[0].time)

            if (
                p.haslayer(TCP)
                and (packet_elapsed_time >= beginning / 1000)
                and (packet_elapsed_time < end / 1000)
                and (p[TCP].sport in connection or p[TCP].dport in connection)
            ):
                if p[IP].src == server_ip:  # downlink
                    dl_05 = dl_05 + (int(len(p[IP])) * 8)
                    dc_05 = dc_05 + 1
                    if int(len(p)) >= 100:  # ignore ack pk
                        dc_gt100_05 = dc_gt100_05 + 1

                    packets_time_05.append(float(p.time))
                    da_05 = float(p.time - dt_05)
                    d_ia_05.append(da_05)
                    dt_05 = p.time
                    d_pk_size_05.append(int(len(p[IP])))
                    if int(len(p)) >= 100:  # ignore ack pk
                        d_packets_gt_100_time.append(p.time)
                        d_pk_size_gt100_05.append(int(len(p[IP])))

                if p[IP].dst == server_ip:  # uplink
                    ul_05 = ul_05 + (int(len(p[IP])) * 8)
                    uc_05 = uc_05 + 1
                    if int(len(p)) >= 100:  # ignore ack pk
                        uc_gt100_05 = uc_gt100_05 + 1

                    ## ia and packet size
                    u_packets_time_05.append(float(p.time))
                    ua_05 = float(p.time - ut_05)
                    u_ia_05.append(ua_05)
                    ut_05 = p.time
                    u_pk_size_05.append(int(len(p[IP])))
                    if int(len(p)) >= 100:  # ignore ack pk
                        u_packets_gt_100_time.append(p.time)
                        u_pk_size_gt100_05.append(int(len(p[IP])))
        # -----------------------------------Download Block------------------------
        if packets_time_05:
            if dc_05 > 2:
                tpTime_05 = packets_time_05[-1] - packets_time_05[0]
                std_less = np.std(d_pk_size_05)
            else:
                tpTime_05 = 1
                std_less = 0

            if dc_gt100_05 > 2:
                tpTime_05_GT100 = d_packets_gt_100_time[-1] - d_packets_gt_100_time[0]
                AvgTime_List_GT100 = [
                    d_packets_gt_100_time[i + 1] - d_packets_gt_100_time[i]
                    for i in range(len(d_packets_gt_100_time) - 1)
                ]
                AvgTime_GT100 = Average(AvgTime_List_GT100)
                std_grt = np.std(d_pk_size_gt100_05)
            else:
                AvgTime_GT100 = 0
                tpTime_05_GT100 = 0
                std_grt = 0

            TP_05 = dl_05 / tpTime_05
            TP_05_Time = dl_05 / segment_time

            # Average time between packets
            time_between_each_packets_05 = [
                packets_time_05[i + 1] - packets_time_05[i]
                for i in range(len(packets_time_05) - 1)
            ]
            average_05 = Average(time_between_each_packets_05)

            tms_string = ""
            for tms in packets_time_05:
                tms_string = tms_string + str(tms) + "~"

            pkt_string = ""
            for pk in d_pk_size_05:
                pkt_string = pkt_string + str(pk) + "~"

            d_packet_gt100_time_str = ""
            for dpg100t in d_packets_gt_100_time:
                d_packet_gt100_time_str = d_packet_gt100_time_str + str(dpg100t) + "~"

            d_packet_gt100_str = ""
            for dpg100 in d_pk_size_gt100_05:
                d_packet_gt100_str = d_packet_gt100_str + str(dpg100) + "~"

            df = df.append(
                pd.Series(
                    [
                        end,
                        tpTime_05,
                        tpTime_05_GT100,
                        average_05,
                        AvgTime_GT100,
                        TP_05,
                        TP_05_Time,
                        dc_05,
                        dc_gt100_05,
                        std_less,
                        std_grt,
                        tms_string,
                        pkt_string,
                        d_packet_gt100_time_str,
                        d_packet_gt100_str,
                    ],
                    index=df.columns,
                ),
                ignore_index=True,
            )
            df.to_csv(
                (
                    pathlib.Path(experiment_result["experiment_folder"]) / "qos.csv"
                ).as_posix(),
                index=False,
                header=True,
            )

    merged_columns = pd.merge(godash_result, df, on="Arr_time", how="left")
    merged_columns.to_csv(
        (pathlib.Path(experiment_result["experiment_folder"]) / "all.csv").as_posix(),
        index=False,
        header=True,
    )


def process_pcap_quic(experiment_result: "ExperimentResult"):
    server_ip = experiment_result["server_ip"]

    pcap = rdpcap(experiment_result["experiment_host_pcap_path"])

    godash_result = get_godash_result_as_dataframe(
        experiment_result["experiment_godash_result_path"]
    )
    godash_timestamps = godash_result["Arr_time"]
    godash_timestamps_before = pd.concat(
        [pd.Series([0]), godash_timestamps[:-1]], ignore_index=True
    )
    godash_timestamps_after = godash_timestamps[0:]

    connection = []
    for ppp in pcap:
        if (
            experiment_result["experiment"]["server_protocol"] == "quic"
            and ppp.haslayer(UDP)
            and ppp.haslayer(IP)
        ):
            if ppp[IP].dst == server_ip or ppp[IP].src == server_ip:
                connection.append(ppp)

    df = pd.DataFrame(
        columns=[
            "Arr_time",
            "interIntervalTimeDP",
            "interIntervalTimeDP_GT100",
            "AvgTimeBWDPK",
            "AvgTimeBWDPK_GT100",
            "DThroughput",
            "DTTime",
            "DTotal_Packets",
            "DTotal_Packets_GT100",
            "STD_Less",
            "STD_GT",
            "DP_Times_str",
            "Packets_str",
            "GT100_Times_str",
            "GT100_Packets_str",
        ]
    )
    for beginning, end in zip(godash_timestamps_before, godash_timestamps_after):
        segment_time = (end - beginning) / 1000

        dl_05 = 0
        dc_05 = 0
        dc_gt100_05 = 0
        da_05 = 0
        dt_05 = 0
        packets_time_05 = []
        d_ia_05 = []
        d_pk_size_05 = []
        d_pk_size_gt100_05 = []
        ul_05 = 0
        uc_gt100_05 = 0
        ua_05 = 0
        ut_05 = 0
        uc_05 = 0
        u_ia_05 = []
        u_pk_size_05 = []
        u_pk_size_gt100_05 = []
        d_packets_gt_100_time = []
        u_packets_time_05 = []
        u_packets_gt_100_time = []

        for p in connection:
            packet_elapsed_time = float(p.time - pcap[0].time)

            if (packet_elapsed_time >= beginning / 1000) and (
                packet_elapsed_time < end / 1000
            ):
                if p[IP].src == server_ip:  # downlink
                    dl_05 = dl_05 + (int(len(p[IP])) * 8)
                    dc_05 = dc_05 + 1
                    if int(len(p)) >= 100:  # ignore ack pk
                        dc_gt100_05 = dc_gt100_05 + 1

                    packets_time_05.append(float(p.time))
                    da_05 = float(p.time - dt_05)
                    d_ia_05.append(da_05)
                    dt_05 = p.time
                    d_pk_size_05.append(int(len(p[IP])))
                    if int(len(p)) >= 100:  # ignore ack pk
                        d_packets_gt_100_time.append(p.time)
                        d_pk_size_gt100_05.append(int(len(p[IP])))

                if p[IP].dst == server_ip:  # uplink
                    ul_05 = ul_05 + (int(len(p[IP])) * 8)
                    uc_05 = uc_05 + 1
                    if int(len(p)) >= 100:  # ignore ack pk
                        uc_gt100_05 = uc_gt100_05 + 1

                    ## ia and packet size
                    u_packets_time_05.append(float(p.time))
                    ua_05 = float(p.time - ut_05)
                    u_ia_05.append(ua_05)
                    ut_05 = p.time
                    u_pk_size_05.append(int(len(p[IP])))
                    if int(len(p)) >= 100:  # ignore ack pk
                        u_packets_gt_100_time.append(p.time)
                        u_pk_size_gt100_05.append(int(len(p[IP])))
        # -----------------------------------Download Block------------------------
        if packets_time_05:
            if dc_05 > 2:
                tpTime_05 = packets_time_05[-1] - packets_time_05[0]
                std_less = np.std(d_pk_size_05)
            else:
                tpTime_05 = 1
                std_less = 0

            if dc_gt100_05 > 2:
                tpTime_05_GT100 = d_packets_gt_100_time[-1] - d_packets_gt_100_time[0]
                AvgTime_List_GT100 = [
                    d_packets_gt_100_time[i + 1] - d_packets_gt_100_time[i]
                    for i in range(len(d_packets_gt_100_time) - 1)
                ]
                AvgTime_GT100 = Average(AvgTime_List_GT100)
                std_grt = np.std(d_pk_size_gt100_05)
            else:
                AvgTime_GT100 = 0
                tpTime_05_GT100 = 0
                std_grt = 0

            TP_05 = dl_05 / tpTime_05
            TP_05_Time = dl_05 / segment_time

            # Average time between packets
            time_between_each_packets_05 = [
                packets_time_05[i + 1] - packets_time_05[i]
                for i in range(len(packets_time_05) - 1)
            ]
            average_05 = Average(time_between_each_packets_05)

            tms_string = ""
            for tms in packets_time_05:
                tms_string = tms_string + str(tms) + "~"

            pkt_string = ""
            for pk in d_pk_size_05:
                pkt_string = pkt_string + str(pk) + "~"

            d_packet_gt100_time_str = ""
            for dpg100t in d_packets_gt_100_time:
                d_packet_gt100_time_str = d_packet_gt100_time_str + str(dpg100t) + "~"

            d_packet_gt100_str = ""
            for dpg100 in d_pk_size_gt100_05:
                d_packet_gt100_str = d_packet_gt100_str + str(dpg100) + "~"

            df = df.append(
                pd.Series(
                    [
                        end,
                        tpTime_05,
                        tpTime_05_GT100,
                        average_05,
                        AvgTime_GT100,
                        TP_05,
                        TP_05_Time,
                        dc_05,
                        dc_gt100_05,
                        std_less,
                        std_grt,
                        tms_string,
                        pkt_string,
                        d_packet_gt100_time_str,
                        d_packet_gt100_str,
                    ],
                    index=df.columns,
                ),
                ignore_index=True,
            )
            df.to_csv(
                (
                    pathlib.Path(experiment_result["experiment_folder"]) / "qos.csv"
                ).as_posix(),
                index=False,
                header=True,
            )

    merged_columns = pd.merge(godash_result, df, on="Arr_time", how="left")
    merged_columns.to_csv(
        (pathlib.Path(experiment_result["experiment_folder"]) / "all.csv").as_posix(),
        index=False,
        header=True,
    )


def process_pcap(experiment_result: "ExperimentResult"):
    if experiment_result["experiment"]["server_protocol"] == "quic":
        process_pcap_quic(experiment_result)
    else:
        process_pcap_tcp(experiment_result)


def merge_all_experiments_into_csv(experiments_root: str):
    experiments_all = set()
    experiments_results = set()

    for path in Path(experiments_root).rglob("all.csv"):
        experiments_all.add(os.path.dirname(path))

    for path in Path(experiments_root).rglob("result.json"):
        experiments_results.add(os.path.dirname(path))

    valid_experiments = experiments_all.intersection(experiments_results)

    all_results = pd.DataFrame()

    for path in valid_experiments:
        with open(os.path.join(path, "result.json"), "r") as f:
            experiment_result: "ExperimentResult" = json.load(f)

        result: pd.DataFrame = pd.read_csv(os.path.join(path, "all.csv"))  # type: ignore
        result["mode"] = experiment_result["experiment"]["mode"]
        result["id"] = experiment_result["experiment"]["id"]
        result["server_protocol"] = experiment_result["experiment"]["server_protocol"]
        result["server_type"] = experiment_result["experiment"]["server_type"]
        result["video_name"] = experiment_result["experiment"]["mpd_path"].split("/")[3]

        all_results = pd.concat([all_results, result], ignore_index=True)

    all_results.to_csv(
        os.path.join("/home/steckhelena", "all_results.csv"), index=False, header=True
    )


def cleanup_pcap(experiment_result: "ExperimentResult"):
    os.remove(experiment_result["experiment_host_pcap_path"])


if __name__ == "__main__":
    merge_all_experiments_into_csv("experiment_results")
