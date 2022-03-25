#!/bin/bash

R=$1
axis=$2
ls -1 OUTPUT_FILES/*.${axis}.xyz > moviedata.lst
ra=`echo $R | awk -F"/" '{print ($2-$1)/($4-$3)}'`
J=`awk 'BEGIN {print "X"2.4*"'$ra'""i/2.4i"}'`



cat << eof > main.sh
cat << Eof > vel.cpt
-30 0 0 255 0 255 255 255
0 255 255 255 30 255 0 0
B 0 0 255
F 255 0 0
Eof
if [ $axis == "y" ]; then
    awk '{print \$3,2000}' `pwd`/DATA/STATIONS > sta.xz
    awk '{print \$2,\$3}' `pwd`/interface > tmp.inter
else
    awk '{print \$4,2000}' `pwd`/DATA/STATIONS > sta.xz
    awk '{print \$1,\$3}' `pwd`/interface > tmp.inter
fi
gmt begin
    gmt psbasemap -R$R -J$J -Bxaf+l"$axis (m)" -Byaf+l"Z (m)" -BWSne -X1.2i -Y1i --PS_MEDIA=17ix3.8i
    gmt plot sta.xz -Si6p -G0 -N
    gmt surface \${MOVIE_TEXT} -I1000/1500 -Gtmp.grd -R$R
    gmt plot tmp.inter -W1.5p
    awk '\$3>2||\$3<-2{print \$0}' `pwd`/\${MOVIE_TEXT} | gmt mask -I1000/1000 -S2000
    gmt grdimage tmp.grd -Cvel.cpt
    gmt mask -C
    printf "0 500 \${MOVIE_TEXT} "| gmt text -F+f12p,Helvetica+jTL -N 
gmt end
eof

gmt movie main.sh -C17ix3.8ix100 -Nforward -Tmoviedata.lst -A+l -D3

rm vel.cpt main.sh moviedata.lst sta.xz tmp.inter
# rm -rf forward

