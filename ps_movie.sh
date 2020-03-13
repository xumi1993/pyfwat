#!/bin/bash
ls -1 OUTPUT_FILES/*.xyz > moviedata.lst

cat << eof > vel.cpt
-100 0 0 255 0 255 255 255
0 255 255 255 100 255 0 0
B 0 0 255
F 255 0 0
eof

cat << eof > main.sh
gmt begin
    gmt psbasemap -R0/100000/-60000/0 -Jx0.005p -Bxaf+l"X (m)" -Byaf+l"Z (m)" -BWSne -X1i -Y1i --PS_MEDIA=9.6ix5.4i
    gmt surface \${MOVIE_TEXT} -I1000/1500 -Gtmp.grd -R0/100000/-60000/0
    gmt grdimage tmp.grd -Cvel.cpt
    printf "0 500 \${MOVIE_TEXT} "| gmt text -F+f12p,Helvetica+jTL -N 
gmt end
eof

gmt movie main.sh -C9.6ix5.4ix100 -Nforward -Tmoviedata.lst -A+l -D3

rm vel.cpt main.sh moviedata.lst
rm -rf forward

