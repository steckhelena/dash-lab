#!/bin/bash
intf=$1
net=$2
bw_array=()
second_link=()
burst=()
b=1
d=1
while IFS=, read -r col1
 do
    bw_array[$b]=$col1
    #second_link[$b]=$col1
    #burst[$d]=$col2 
    #echo "I got:$col1|$col3"
    b=$((b + 1))
    d=$((d + 1))
done < 'Band_data/Band_data/5g/'${net}.csv


#------------------------------------------------------------------------------------#
#this role variable, first enable the TC then it delete the rule going in Else, but when It delete, it again enable new rule
role=1
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
t=1
j=0
while [[ true ]]
do
    
    tc qdisc add dev ${intf} root handle 1: htb default 1
    tc class add dev ${intf} parent 1: classid 1:1 htb rate "${bw_array[t]}"kbit ceil "${bw_array[t]}"kbit

    echo  ${bw_array[t]}
    t=$((t + 1))
    sleep 4
    tc qdisc del dev ${intf} root
    
    num=$(ps -ef| grep  godash| wc -l)
    echo "Num ---- ";
    echo $num;
    if [ $num -eq 1 ]; then
            sleep 1
            echo  "Streaming done..."
            echo  "Stop pcap capturing..."
            echo  "Stop server...."

            sudo pkill -9 tcpdump
            sudo pkill -9 caddy
            sudo pkill -9 hypercorn

            break
    fi
done
