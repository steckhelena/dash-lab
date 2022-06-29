#!/bin/bash
mod=$1
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
done < 'Band_data/Band_data/5g/'$net.csv


#------------------------------------------------------------------------------------#
#this role variable, first enable the TC then it delete the rule going in Else, but when It delete, it again enable new rule
role=1
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
t=1
j=0
while [[ $(date -u +%s) -le $endtime ]]
do
    
    tc qdisc add dev s2-eth1 root handle 1: htb default 1
    
    
    # create class 1:1 and limit rate to 6Mbit
    sudo tc class add dev s2-eth1 parent 1: classid 1:1 htb rate "${bw_array[t]}"kbit ceil "${bw_array[t]}"kbit
    
   
    #tc qdisc show  dev $1
    echo  ${bw_array[t]}
    #echo  ${second_link[t]}
    t=$((t + 1))
    sleep 4
    tc qdisc del dev s2-eth1 root
    
    num=$(ps -ef| grep  godash| wc -l)
    echo "Num ---- ";
    echo $num;
    if [ $num -eq 4 ]; then
            sleep 1
            sudo chmod 777 -R /home/raza/Downloads/goDASH/godash/data/
            echo  "Streaming done..."
            echo  "Stop pcap capturing..."
            echo  "Stop server...."
         #   
            sudo pkill -9 tcpdump
            sudo pkill -9 caddy
            sudo pkill -9 hypercorn
            #cd /home/dash/testbed/D-ITG-2.8.1-r1023/bin/ && ./ITGDec receiver.log 
            #pkill ITGRecv
            #b=$((b + 1))

            break
    fi

     
done
