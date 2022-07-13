# DASHLab: A simplified CLI to power DASH experiments with traffic control

This is my Final Coursework for Computer Engineering at Unicamp University,
supervised by Christian Esteve Rothenberg, and made with help from Raza Ul
Mustafa.

This project aims to provide an easy-to-use interface for quickly spinning up
experiments for measuring DASH QoE(Quality of Experience) and QoS(Quality of
Service) features for each segment of a DASH video.

Additionally, this project aims to do that by simulating network conditions based
on a trace file. The trace files must be in a format similar to the ones in the
_Beyond Throughput, The Next Generation: a 5G Dataset with Channel and Context
Metrics_\[1\] work.

When the project is ran it runs one experiment per combination of the following:

- Protocols: QUIC or TCP
- Server Types: WSGI or ASGI
- Adaptation Algorithms: bba, conventional, elastic or logistic
- MPD files: all of the provided to be hosted on a file server
- Traces: all of the provided traces
- Repetitions: the number each experiment will run.

This project has a checkpoint feature, meaning that it can auto-resume from
where it stopped running, which is useful for long-running tasks.

## Requirements

For running this CLI it is necessary to have certain packages installed:

- godash\[2\]\[3\]
- python >= 3.8, with the following packages:
  - numpy
  - pandas
  - scapy(for reading pcap files and extracting QoS features)
  - hypercorn
  - mininet\[4\]
  - jinja2
- mininet

You also need to enable the ifb kernel module with `sudo modprobe ifb` for
traffic control on the download packets on the host node.

## Usage

```
usage: lab.py [-h] --godash-bin GODASH_BIN
              [--godash-config-template GODASH_CONFIG_TEMPLATE] -m MPD_PATH
              [-d DATASET] [-t DATASET_TYPE] [-r REPETITIONS]
              [--algos {bba,conventional,elastic,logistic} [{bba,conventional,elastic,logistic} ...]]
              [--protocols {tcp,quic} [{tcp,quic} ...]]
              [--types {wsgi,asgi} [{wsgi,asgi} ...]]
              [--experiment-root EXPERIMENT_ROOT] [-c] [--no-use-checkpoint]
              [-v]

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


optional arguments:
  -h, --help            show this help message and exit
  --godash-bin GODASH_BIN
                        <Required> Path to goDASH executable. (default: None)
  --godash-config-template GODASH_CONFIG_TEMPLATE
                        Path to goDASH configuration template. This will be
                        the base for the goDASH configuration, the fields
                        'quic', 'url' 'serveraddr' and 'adapt' will be
                        overwritten for the running experiment. The other
                        fields will stay the same. (default: /home/raza/dash-
                        lab/godash_defaults/configure.json)
  -m MPD_PATH, --mpd-path MPD_PATH
                        <Required> Path from the server root to the mpd files
                        with information on the DASH videos to be streamed.
                        Can be added multiple times. E.g.: `-m a/b.mpd -m
                        b/c.mpd` (default: None)
  --dash-files-root DASH_FILES_ROOT
                        This is the root to the DASH files to be served by
                        the file server, i.e. the path where the DASH
                        segments are stored, the mpd paths are relative to
                        this. (default: /var/www/html)
  -d DATASET, --dataset DATASET
                        System path, relative or absolute, to the dataset
                        which will be used to simulate the network
                        conditions, can be added multiple times, requires one
                        -t/--dataset-type set for each. E.g.: `-d a/b.csv
                        -t4g -d b/c.csv -t5g`. If not provided defaults to
                        the datasets from [1]. (default: None)
  -t DATASET_TYPE, --dataset-type DATASET_TYPE
                        Type of the dataset. E.g.: 5g, 4g, 3g. (default:
                        None)
  -r REPETITIONS, --repetitions REPETITIONS
                        Number of repetitions for each experiment
                        combination. (default: 5)
  --algos {bba,conventional,elastic,logistic} [{bba,conventional,elastic,logistic} ...]
                        What algorithms to run the experiments with.
                        (default: ['bba', 'conventional', 'elastic',
                        'logistic'])
  --protocols {tcp,quic} [{tcp,quic} ...]
                        What protocols to run the experiments with. (default:
                        ['tcp', 'quic'])
  --types {wsgi,asgi} [{wsgi,asgi} ...]
                        What kind of server gateway to run the experiments
                        with. (default: ['wsgi', 'asgi'])
  --experiment-root EXPERIMENT_ROOT
                        The experiment output folder path, can be relative or
                        absolute. (default: experiment_results)
  -c, --use-checkpoint  Use a checkpoint file for easily resuming experiments
                        execution if stopped. Defaults to using a checkpoint.
                        (default: True)
  --no-use-checkpoint   Do not use a checkpoint file for easily resuming
                        experiments execution if stopped. Defaults to using a
                        checkpoint. (default: True)
  -v, --verbose         Makes output verbose. (default: False)

```

## References:

[1] D. Raca, D. Leahy, C.J. Sreenan and J.J. Quinlan. Beyond Throughput, The
Next Generation: A 5G Dataset with Channel and Context Metrics. ACM Multimedia
Systems Conference (MMSys), Istanbul, Turkey. June 8-11, 2020

[2] D. Raca, M. Manifacier, and J.J. Quinlan. goDASH - GO accelerated HAS
framework for rapid prototyping. 12th International Conference on Quality of
Multimedia Experience (QoMEX), Athlone, Ireland. 26th to 28th May, 2020 CORA

[3] John O’Sullivan, D. Raca, and Jason J. Quinlan. Demo Paper: godash 2.0 - The
Next Evolution of HAS Evaluation. 21st IEEE International Symposium On A World
Of Wireless, Mobile And Multimedia Networks (IEEE WoWMoM 2020), Cork, Ireland.
August 31 to September 03, 2020 CORA

[4] https://github.com/mininet/mininet

[5] R. Ul Mustafa, M. T. Islam, C. Rothenberg, S. Ferlin, D. Raca and J. J.
Quinlan, "DASH QoE Performance Evaluation Framework with 5G Datasets," 2020 16th
International Conference on Network and Service Management (CNSM), Izmir,
Turkey, 2020, pp. 1-6, doi: 10.23919/CNSM50824.2020.9269111.
