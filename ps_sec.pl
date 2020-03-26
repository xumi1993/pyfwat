#!/usr/bin/env perl
$data = $ARGV[0];
$xmin = `grep ^LONGITUDE_MIN DATA/meshfem3D_files/Mesh_Par_file | grep -v -E '^[[:space:]]*#' | cut -d = -f 2`;
chomp($xmin);
$xmin = sprintf "%-.1f", $xmin;
$xmax = `grep ^LONGITUDE_MAX DATA/meshfem3D_files/Mesh_Par_file | grep -v -E '^[[:space:]]*#' | cut -d = -f 2`;
chomp($xmax);
$xmax = sprintf "%-.1f", $xmax;
$zmax = `grep ^DEPTH_BLOCK_KM DATA/meshfem3D_files/Mesh_Par_file | grep -v -E '^[[:space:]]*#' | cut -d = -f 2`*-1000;
chomp($zamx);
$ratio = ($xmax-$xmin)/(0-$zmax);
$short_len = 1.4;
$long_len = $ratio*$short_len;
$name = "sec";
$ps = $name.".ps";

open(cpt, ">gray.cpt");
print cpt "3000 255 255 255 6000 200 200 200\n";
print cpt "F 200\n";
print cpt "B 255\n";
print cpt "N 255\n";
close(cpt);

$shift = $long_len+0.4;
`gmt psbasemap -R$xmin/$xmax/$zmax/0 -JX${long_len}i/${short_len}i -Bxaf+L"X (m)" -Byaf+L"Z (m)" -BWSne -K -X2i> $ps`;
`awk '\$2==0{print \$3,\$1,\$4}' $data|gmt surface -I1000/1500 -Gtmp.grd -R`;
`gmt makecpt -Cgray.cpt -T3000/5000/10 -Z > tmp.cpt`;
`gmt grdimage -R -J -O -K -Ctmp.cpt tmp.grd >> $ps`;
`gmt psscale -Ctmp.cpt -DjML+w3c/0.3c+o${shift}i/0i -Bxafg+l"Vs (m/s)" -R -J -O -K >> $ps`;
`gmt psxy -R -J -O -T >> $ps`;
`gmt psconvert -A -P -Tg $ps`;
`rm tmp.* $ps gmt* gray.cpt`;