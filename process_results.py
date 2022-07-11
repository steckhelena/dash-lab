import numpy as np
import pandas as pd
from scapy.all import rdpcap
from scapy.layers.inet import IP, TCP

server_ip = "10.0.0.1"

windows_size = 5

pcap = rdpcap("/sta1-eth0.pcap")


def Average(lst):
    if lst:
        return sum(lst) / len(lst)
    else:
        return 0


connection = []
flag = True
for ppp in pcap:
    if ppp.haslayer(TCP):
        if ppp[IP].dst == server_ip:
            if ppp[TCP].flags == "FA" or ppp[TCP].flags == "F":
                connection.append(ppp[TCP].sport)

df = pd.DataFrame(
    columns=[
        "Time",
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
for i in np.arange(0, 240, windows_size):
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
        if (
            (p.haslayer(TCP))
            and ((float(p.time - pcap[0].time)) >= i)
            and ((float(p.time - pcap[0].time)) < i + windows_size)
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
            print(dc_gt100_05)
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

        u_tpTime_05 = u_packets_time_05[-1] - u_packets_time_05[0]
        # here last packet time minus first packet time, divided by all packets from server

        TP_05 = dl_05 / tpTime_05
        TP_05_Time = dl_05 / windows_size

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
                    i,
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
        df.to_csv(folder + "/qos.csv", index=None, header=True)
