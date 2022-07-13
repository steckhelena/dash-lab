#!/bin/bash

python3 lab.py \
    -m "4K_non_copyright_dataset/2_sec/x264/bbb/DASH_Files/full/bbb_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/2_sec/x264/sintel/DASH_Files/full/sintel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/2_sec/x264/tearsofsteel/DASH_Files/full/tearsofsteel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/4_sec/x264/bbb/DASH_Files/full/bbb_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/4_sec/x264/sintel/DASH_Files/full/sintel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/4_sec/x264/tearsofsteel/DASH_Files/full/tearsofsteel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/6_sec/x264/bbb/DASH_Files/full/bbb_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/6_sec/x264/sintel/DASH_Files/full/sintel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/6_sec/x264/tearsofsteel/DASH_Files/full/tearsofsteel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/8_sec/x264/bbb/DASH_Files/full/bbb_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/8_sec/x264/sintel/DASH_Files/full/sintel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/8_sec/x264/tearsofsteel/DASH_Files/full/tearsofsteel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/10_sec/x264/bbb/DASH_Files/full/bbb_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/10_sec/x264/sintel/DASH_Files/full/sintel_enc_x264_dash.mpd" \
    -m "4K_non_copyright_dataset/10_sec/x264/tearsofsteel/DASH_Files/full/tearsofsteel_enc_x264_dash.mpd" \
    -d "RazaDatasets/4g/B_2017.12.17_14.16.19.csv" -t4g\
    -d "RazaDatasets/4g/B_2018.01.27_13.58.28.csv" -t4g\
    -d "RazaDatasets/4g/B_2018.02.12_16.14.01.csv" -t4g\
    -d "RazaDatasets/5g/Static/B_2019.12.16_13.40.04.csv" -t5g\
    -d "RazaDatasets/5g/Static/B_2020.01.16_10.43.34.csv" -t5g\
    -d "RazaDatasets/5g/Static/B_2020.02.13_13.57.29.csv" -t5g\
    -d "RazaDatasets/5g/Static/B_2020.02.14_13.21.26.csv" -t5g\
    -d "RazaDatasets/5g/Static/B_2020.02.27_18.39.27.csv" -t5g\
    --godash-bin "/home/raza/Downloads/goDASH/godash/godash" \
    --godash-config-template "/home/raza/Downloads/goDASHbed/config/configure.json" \
    --types wsgi
