import os
import subprocess
import sys

# mode=['3g','4g','5g'] #network type '5g','3g','4g','5g'
mode = ["5g"]  # network type '5g','3g','4g','5g'

host = [1]  # number of host

algo = ["conventional"]  # adaptation algorithm  'elastic','bba','logistic'

# net3= ['train', 'ferry','car','bus','metro'] # mobility for 3g
# net3= ['metro']
# net4=['bus', 'train', 'static','car','pedestrian'] # mobility for 4g
# net4=['pedestrian']
# net5=[ 'Static-1','Static-2', 'Static-3', 'Driving-1', 'Driving-2','Driving-3']

net5 = ["Driving-8"]

#'A_A_Static','A_A_Driving','N_A_Driving',, ,,'D_Driving'


prot = ["quic"]

sertype = ["WSGI"]

count = ["2"]

for curr in count:
    for md in mode:
        if md == "5g":
            for i in net5:
                # for j in doc5:
                for k in sertype:
                    for l in host:
                        for m in algo:
                            for p in prot:
                                clear = "sudo mn -c"
                                test3 = (
                                    "sudo python3 test3.py "
                                    + str(md)
                                    + " "
                                    + str(i)
                                    + " "
                                    + str(l)
                                    + " "
                                    + str(m)
                                    + " "
                                    + str(p)
                                    + " "
                                    + str(k)
                                    + " "
                                    + str(curr)
                                )
                                subprocess.run(clear.split(" "))
                                print(test3)
                                subprocess.run(test3.split(" "))
        elif md == "4g":
            for i in net4:
                # for j in doc4:
                for k in sertype:
                    for l in host:
                        for m in algo:
                            for p in prot:
                                clear = "sudo mn -c"
                                test3 = (
                                    "sudo python test3.py "
                                    + str(md)
                                    + " "
                                    + str(i)
                                    + " "
                                    + str(l)
                                    + " "
                                    + str(m)
                                    + " "
                                    + str(p)
                                    + " "
                                    + str(k)
                                    + " "
                                    + str(curr)
                                )
                                subprocess.run(clear.split(" "))
                                print(test3)
                                subprocess.run(test3.split(" "))
        else:
            for i in net3:
                # for j in doc3:
                for k in sertype:
                    for l in host:
                        for m in algo:
                            for p in prot:
                                clear = "sudo mn -c"
                                test3 = (
                                    "sudo python test3.py "
                                    + str(md)
                                    + " "
                                    + str(i)
                                    + " "
                                    + str(l)
                                    + " "
                                    + str(m)
                                    + " "
                                    + str(p)
                                    + " "
                                    + str(k)
                                    + " "
                                    + str(curr)
                                )
                                subprocess.run(clear.split(" "))
                                print(test3)
                                subprocess.run(test3.split(" "))
