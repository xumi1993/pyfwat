#!/bin/bash

R=$1
axis=$2
ls -1 OUTPUT_FILES/*_${axis}_*.xyz > moviedata.lst
ra=`echo $R | awk -F"/" '{print ($2-$1)/($4-$3)}'`
J=`awk 'BEGIN {print "X"2.4*"'$ra'""i/2.4i"}'`
cat << eof > vel.cpt
-5 0 0 255 0 255 255 255
0 255 255 255 5 255 0 0
B 0 0 255
F 255 0 0
eof
if [ $axis == "Y" ]; then
    awk '{print $3,2000}' DATA/STATIONS > sta.xz
    awk '{print $2,$3}' interface > tmp.inter
else
    awk '{print $4,2000}' DATA/STATIONS > sta.xz
    awk '{print $1,$3}' interface > tmp.inter
fi
# ./create_interf.py > interface
cat << eof > main.sh
gmt begin
    gmt psbasemap -R$R -J$J -Bxaf+l"$axis (m)" -Byaf+l"Z (m)" -BWSne -X1.2i -Y1i --PS_MEDIA=17ix3.8i
    gmt plot sta.xz -Si6p -G0 -N
    gmt surface \${MOVIE_TEXT} -I1000/1500 -Gtmp.grd -R$R
    gmt grdimage tmp.grd -Cvel.cpt
    gmt plot tmp.inter -W1.5p
    printf "0 500 \${MOVIE_TEXT} "| gmt text -F+f12p,Helvetica+jTL -N 
gmt end
eof

gmt movie main.sh -C17ix3.8ix100 -Nforward -Tmoviedata.lst -A+l -D3

rm vel.cpt main.sh moviedata.lst sta.xz tmp.inter
# rm -rf forward

