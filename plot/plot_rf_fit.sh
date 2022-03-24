#!/bin/bash

###
if [ $# -eq 4 ];then
    model=$1
    setid=$2
    gauss=$3
    outpath=$4
elif [ $# -gt 4 -o $# -eq 0 ];then
    echo " Usage: ./plot_rf_fit.sh M?? setid [outpath] "
    echo " outpath: defaults to ./figures/ "
    echo " narg: " $#
    exit
else
    model=$1
    setid=$2
    gauss=$3
    outpath="./figures"
fi
###

evtid=`awk '{print $1}' src_rec/sources_set${setid}.dat`
# ls solver/${model}.set${setid}/${evtid}/OUTPUT_FILES/dat.*.F${gauss} > saclst_dat
saclst knetwk kstnm f data/${evtid}/*.F${gauss}.rf.sac > saclst_dat
awk '{print FNR" a "$2"."$3}' saclst_dat > yticklabel.txt
ls solver/${model}.set${setid}/${evtid}/OUTPUT_FILES/syn.*.F${gauss} > saclst_syn
gmt begin ${outpath}/${model}.set${setid}_rf_fit_F${gauss} png
    gmt set FONT_TITLE=14p
    gmt set MAP_GRID_PEN=0.3p,gray
    gmt basemap -R-5/25/0/`awk 'END{print NR+2}' saclst_dat` -Jx0.4c/0.6c -Bxa5f1g5+l"Time after P (s)" -B+t"${model}, Event: ${setid}" -Bpycyticklabel.txt
    awk '{print $1}' saclst_dat|gmt sac -W1p -En1 -M0.1
    gmt sac saclst_syn -W1p,red -En1 -M0.1
gmt end
rm saclst_dat saclst_syn yticklabel.txt