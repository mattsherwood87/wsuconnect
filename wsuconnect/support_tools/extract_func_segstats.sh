#!/bin/bash

echo 'SubjID,L_bankssts_mean,L_caudalanteriorcingulate_mean,L_caudalmiddlefrontal_mean,L_cuneus_mean,L_entorhinal_mean,L_fusiform_mean,L_inferiorparietal_mean,L_inferiortemporal_mean,L_isthmuscingulate_mean,L_lateraloccipital_mean,L_lateralorbitofrontal_mean,L_lingual_mean,L_medialorbitofrontal_mean,L_middletemporal_mean,L_parahippocampal_mean,L_paracentral_mean,L_parsopercularis_mean,L_parsorbitalis_mean,L_parstriangularis_mean,L_pericalcarine_mean,L_postcentral_mean,L_posteriorcingulate_mean,L_precentral_mean,L_precuneus_mean,L_rostralanteriorcingulate_mean,L_rostralmiddlefrontal_mean,L_superiorfrontal_mean,L_superiorparietal_mean,L_superiortemporal_mean,L_supramarginal_mean,L_frontalpole_mean,L_temporalpole_mean,L_transversetemporal_mean,L_insula_mean,R_bankssts_mean,R_caudalanteriorcingulate_mean,R_caudalmiddlefrontal_mean,R_cuneus_mean,R_entorhinal_mean,R_fusiform_mean,R_inferiorparietal_mean,R_inferiortemporal_mean,R_isthmuscingulate_mean,R_lateraloccipital_mean,R_lateralorbitofrontal_mean,R_lingual_mean,R_medialorbitofrontal_mean,R_middletemporal_mean,R_parahippocampal_mean,R_paracentral_mean,R_parsopercularis_mean,R_parsorbitalis_mean,R_parstriangularis_mean,R_pericalcarine_mean,R_postcentral_mean,R_posteriorcingulate_mean,R_precentral_mean,R_precuneus_mean,R_rostralanteriorcingulate_mean,R_rostralmiddlefrontal_mean,R_superiorfrontal_mean,R_superiorparietal_mean,R_superiortemporal_mean,R_supramarginal_mean,R_frontalpole_mean,R_temporalpole_mean,R_transversetemporal_mean,R_insula_mean' > CorticalMeasuresENIGMA_mean.csv


for subj_id in $(ls -d ./sub-*); do #may need to change this so that it selects subjects with FS output

echo `basename $subj_id`

for ses_num in $(ls -d ${subj_id}/ses-*); do

subj=`basename $subj_id`
ses=`basename $ses_num`
echo -e "\t$ses"

printf "%s,"  "${subj}_${ses}" >> CorticalMeasuresENIGMA_mean.csv

for side in lh rh; do

for x in ctx-${side}-bankssts ctx-${side}-caudalanteriorcingulate ctx-${side}-caudalmiddlefrontal ctx-${side}-cuneus ctx-${side}-entorhinal ctx-${side}-fusiform ctx-${side}-inferiorparietal ctx-${side}-inferiortemporal ctx-${side}-isthmuscingulate ctx-${side}-lateraloccipital ctx-${side}-lateralorbitofrontal ctx-${side}-lingual ctx-${side}-medialorbitofrontal ctx-${side}-middletemporal ctx-${side}-parahippocampal ctx-${side}-paracentral ctx-${side}-parsopercularis ctx-${side}-parsorbitalis ctx-${side}-parstriangularis ctx-${side}-pericalcarine ctx-${side}-postcentral ctx-${side}-posteriorcingulate ctx-${side}-precentral ctx-${side}-precuneus ctx-${side}-rostralanteriorcingulate ctx-${side}-rostralmiddlefrontal ctx-${side}-superiorfrontal ctx-${side}-superiorparietal ctx-${side}-superiortemporal ctx-${side}-supramarginal ctx-${side}-frontalpole ctx-${side}-temporalpole ctx-${side}-transversetemporal ctx-${side}-insula; do

printf "%g," `grep -w ${x} ${ses_num}/segstats/func/space-highres_zstat1.dat | grep -v lobe | awk '{print $6}'` >> CorticalMeasuresENIGMA_mean.csv
#printf "%g," `grep -w ${x} ${subj_id}/stats/${side} | awk '{print $3}'` >> CorticalMeasuresENIGMA_SurfAvg.csv

done
done

#printf "%g," `cat ${subj_id}/stats/lh.aparc.stats | grep MeanThickness | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_ThickAvg.csv
#printf "%g," `cat ${subj_id}/stats/rh.aparc.stats | grep MeanThickness | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_ThickAvg.csv
#printf "%g," `cat ${subj_id}/stats/lh.aparc.stats | grep MeanThickness | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_SurfAvg.csv
#printf "%g," `cat ${subj_id}/stats/rh.aparc.stats | grep MeanThickness | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_SurfAvg.csv
#printf "%g," `cat ${subj_id}/stats/lh.aparc.stats | grep WhiteSurfArea | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_ThickAvg.csv
#printf "%g," `cat ${subj_id}/stats/rh.aparc.stats | grep WhiteSurfArea | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_ThickAvg.csv
#printf "%g," `cat ${subj_id}/stats/lh.aparc.stats | grep WhiteSurfArea | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_SurfAvg.csv
#printf "%g," `cat ${subj_id}/stats/rh.aparc.stats | grep WhiteSurfArea | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_SurfAvg.csv
#printf "%g" `cat ${subj_id}/stats/aseg.stats | grep IntraCranialVol | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_ThickAvg.csv
#printf "%g" `cat ${subj_id}/stats/aseg.stats | grep IntraCranialVol | awk -F, '{print $4}'` >> CorticalMeasuresENIGMA_SurfAvg.csv

echo "" >> CorticalMeasuresENIGMA_mean.csv

done

#echo "" >> CorticalMeasuresENIGMA_SurfAvg.csv

done
