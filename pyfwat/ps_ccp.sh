#!/bin/bash
name=ccp
ps=$name.ccp
stack_data=stack.dat
vs_data=sec_xz_vs.dat

cat > gray.cpt << eof
3000 255 255 255 6000 180 180 180
F 200
B 255
N 255
eof

gmt psbasemap -R0/200000/-100000/0 -Jx0.003p/0.003p -Bxaf+l"X (m)" -Byaf+l"Z (m)" -BWSne -K -X1.7i > $ps
gmt surface $vs_data -I1000/1500 -Gtmp.grd -R
gmt makecpt -Cgray.cpt -T3/5/0.1 -Z > tmp.cpt
gmt grdimage -R -J -O -K -Ctmp.cpt tmp.grd >> $ps
gmt pswiggle $stack_data -R -J -O -K -A90 -Z1 -G+255/25/25 -G-DEEPSKYBLUE1 -W0.5p -t45 >> $ps
awk '{print $4,$5+2000}' DATA/STATIONS | gmt psxy -R -J -O -K -Si10p -G0 -N >> $ps
gmt psscale -Ctmp.cpt -DjML+w5c/0.3c+o8.6i/0i -Bxafg+l"Vs (km/s)" -R -J -O -K >> $ps

gmt psxy -R -J -O -T >> $ps
gmt psconvert -A -P -Tg $ps
rm gmt* $ps gray.cpt tmp.*