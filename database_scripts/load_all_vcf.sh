#!/bin/bash
CNT=0
for sample_id in "11006.fa" "11006.mo" "11006.p1" "11009.fa" "11009.mo" "11009.p1" "11013.fa" "11013.mo" "11013.p1" "11013.s1" "11023.fa" "11023.mo" "11023.p1" "11029.fa" "11029.mo" "11029.p1" "11029.s1" "11043.fa" "11043.mo" "11043.p1" "11055.fa" "11055.mo" "11055.p1" "11056.fa" "11056.mo" "11056.p1" "11064.fa" "11064.mo" "11064.p1" "11069.fa" "11069.mo" "11069.p1" "11083.fa" "11083.mo" "11083.p1" "11093.fa" "11093.mo" "11093.p1" "11096.fa" "11096.mo" "11096.p1" "11109.fa" "11109.mo" "11109.p1" "11120.fa" "11120.mo" "11120.p1" "11124.fa" "11124.mo" "11124.p1" "11141.fa" "11141.mo" "11141.p1" "11148.fa" "11148.mo" "11148.p1" "11172.fa" "11172.mo" "11172.p1" "11172.s1" "11184.fa" "11184.mo" "11184.p1" "11190.fa" "11190.mo" "11190.p1" "11190.s1" "11193.fa" "11193.mo" "11193.p1" "11195.fa" "11195.mo" "11195.p1" "11198.fa" "11198.mo" "11198.p1" "11205.fa" "11205.mo" "11205.p1" "11218.fa" "11218.mo" "11218.p1" "11224.fa" "11224.mo" "11224.p1" "11229.fa" "11229.mo" "11229.p1" "11229.s1" "11246.fa" "11246.mo" "11246.p1" "11257.fa" "11257.mo" "11257.p1" "11262.fa" "11262.mo" "11262.p1" "11291.fa" "11291.mo" "11291.p1" "11291.s1" "11303.fa" "11303.mo" "11303.p1" "11346.fa" "11346.mo" "11346.p1" "11364.fa" "11364.mo" "11364.p1" "11364.s1" "11375.fa" "11375.mo" "11375.p1" "11388.fa" "11388.mo" "11388.p1" "11390.fa" "11390.mo" "11390.p1" "11390.s1" "11396.fa" "11396.mo" "11396.p1" "11398.fa" "11398.mo" "11398.p1" "11414.fa" "11414.mo" "11414.p1" "11425.fa" "11425.mo" "11425.p1" "11452.fa" "11452.mo" "11452.p1" "11452.s1" "11459.fa" "11459.mo" "11459.p1" "11459.s1" "11469.fa" "11469.mo" "11469.p1" "11469.s1" "11471.fa" "11471.mo" "11471.p1" "11472.fa" "11472.mo" "11472.p1" "11472.s1" "11479.fa" "11479.mo" "11479.p1" "11479.s1" "11480.fa" "11480.mo" "11480.p1" "11491.fa" "11491.mo" "11491.p1" "11491.s1" "11498.fa" "11498.mo" "11498.p1" "11504.fa" "11504.mo" "11504.p1" "11506.fa" "11506.mo" "11506.p1" "11510.fa" "11510.mo" "11510.p1" "11518.fa" "11518.mo" "11518.p1" "11523.fa" "11523.mo" "11523.p1" "11526.fa" "11526.mo" "11526.p1" "11545.fa" "11545.mo" "11545.p1" "11556.fa" "11556.mo" "11556.p1" "11569.fa" "11569.mo" "11569.p1" "11569.s1" "11571.fa" "11571.mo" "11571.p1" "11571.s1" "11587.fa" "11587.mo" "11587.p1" "11599.fa" "11599.mo" "11599.p1" "11610.fa" "11610.mo" "11610.p1" "11610.s1" "11629.fa" "11629.mo" "11629.p1" "11629.s1" "11638.fa" "11638.mo" "11638.p1" "11638.s1" "11653.fa" "11653.mo" "11653.p1" "11659.fa" "11659.mo" "11659.p1" "11659.s1" "11660.fa" "11660.mo" "11660.p1" "11691.fa" "11691.mo" "11691.p1" "11691.s1" "11696.fa" "11696.mo" "11696.p1" "11696.s1" "11707.fa" "11707.mo" "11707.p1"
do
	CNT=$((COUNTER + 1))
	echo $CNT
	scp nkrumm@eeek:/net/eichler/vol17/grc_released_exome_data/${sample_id}*.vcf.variant /Volumes/achiever_vol2/temp/
	java -Xmx4g -jar /Applications/snpEff/snpEff.jar eff -v hg19 -c /Applications/snpEff/snpEff.config /Volumes/achiever_vol2/temp/${sample_id}.*merged.sorted.nodups.realigned.all_reads.genotypes.annotated.filtered.vcf.variant > /Volumes/achiever_vol2/temp/${sample_id}.*merged.sorted.nodups.realigned.all_reads.genotypes.annotated.filtered.vcf.variant.eff

	python import_vcf.py --vcf /Volumes/achiever_vol2/temp/${sample_id}.*merged.sorted.nodups.realigned.all_reads.genotypes.annotated.filtered.vcf.variant.eff --sample_name ${sample_id} --study_name Simons_ASD --filter_name GATK

	rm -f /Volumes/achiever_vol2/temp/${sample_id}*.vcf.variant
	rm -f /Volumes/achiever_vol2/temp/${sample_id}*.vcf.variant.eff
done;

 # "11711.fa" "11711.mo" "11711.p1" "11711.s1" "11715.fa" "11715.mo" "11715.p1" "11715.s1" "11722.fa" "11722.mo" "11722.p1" "11722.s1" "11734.fa" "11734.mo" "11734.p1" "11753.fa" "11753.mo" "11753.p1" "11773.fa" "11773.mo" "11773.p1" "11773.s1" "11788.fa" "11788.mo" "11788.p1" "11788.s1" "11827.fa" "11827.mo" "11827.p1" "11834.fa" "11834.mo" "11834.p1" "11843.fa" "11843.mo" "11843.p1" "11863.fa" "11863.mo" "11863.p1" "11872.fa" "11872.mo" "11872.p1" "11872.s1" "11895.fa" "11895.mo" "11895.p1" "11895.s1" "11928.fa" "11928.mo" "11928.p1" "11942.fa" "11942.mo" "11942.p1" "11942.s1" "11947.fa" "11947.mo" "11947.p1" "11948.fa" "11948.mo" "11948.p1" "11959.fa" "11959.mo" "11959.p1" "11959.s1" "11964.fa" "11964.mo" "11964.p1" "11964.s1" "11969.fa" "11969.mo" "11969.p1" "11989.fa" "11989.mo" "11989.p1" "12011.fa" "12011.mo" "12011.p1" "12011.s1" "12015.fa" "12015.mo" "12015.p1" "12036.fa" "12036.mo" "12036.p1" "12073.fa" "12073.mo" "12073.p1" "12086.fa" "12086.mo" "12086.p1" "12106.fa" "12106.mo" "12106.p1" "12106.s1" "12114.fa" "12114.mo" "12114.p1" "12118.fa" "12118.mo" "12118.p1" "12130.fa" "12130.mo" "12130.p1" "12152.fa" "12152.mo" "12152.p1" "12152.s1" "12153.fa" "12153.mo" "12153.p1" "12153.s1" "12157.fa" "12157.mo" "12157.p1" "12161.fa" "12161.mo" "12161.p1" "12161.s1" "12185.fa" "12185.mo" "12185.p1" "12198.fa" "12198.mo" "12198.p1" "12212.fa" "12212.mo" "12212.p1" "12225.fa" "12225.mo" "12225.p1" "12233.fa" "12233.mo" "12233.p1" "12233.s1" "12237.fa" "12237.mo" "12237.p1" "12238.fa" "12238.mo" "12238.p1" "12249.fa" "12249.mo" "12249.p1" "12285.fa" "12285.mo" "12285.p1" "12285.s1" "12296.fa" "12296.mo" "12296.p1" "12300.fa" "12300.mo" "12300.p1" "12304.fa" "12304.mo" "12304.p1" "12304.s1" "12335.fa" "12335.mo" "12335.p1" "12341.fa" "12341.mo" "12341.p1" "12346.fa" "12346.mo" "12346.p1" "12358.fa" "12358.mo" "12358.p1" "12358.s1" "12373.fa" "12373.mo" "12373.p1" "12373.s1" "12378.fa" "12378.mo" "12378.p1" "12381.fa" "12381.mo" "12381.p1" "12390.fa" "12390.mo" "12390.p1" "12390.s1" "12430.fa" "12430.mo" "12430.p1" "12437.fa" "12437.mo" "12437.p1" "12444.fa" "12444.mo" "12444.p1" "12521.fa" "12521.mo" "12521.p1" "12532.fa" "12532.mo" "12532.p1" "12555.fa" "12555.mo" "12555.p1" "12565.fa" "12565.mo" "12565.p1" "12578.fa" "12578.mo" "12578.p1" "12578.s1" "12581.fa" "12581.mo" "12581.p1" "12581.s1" "12603.fa" "12603.mo" "12603.p1" "12621.fa" "12621.mo" "12621.p1" "12630.fa" "12630.mo" "12630.p1" "12630.s1" "12641.fa" "12641.mo" "12641.p1" "12667.fa" "12667.mo" "12667.p1" "12674.fa" "12674.mo" "12674.p1" "12703.fa" "12703.mo" "12703.p1" "12703.s1" "12741.fa" "12741.mo" "12741.p1" "12741.s1" "12744.fa" "12744.mo" "12744.p1" "12752.fa" "12752.mo" "12752.p1" "12810.fa" "12810.mo" "12810.p1" "12810.s1" "12905.fa" "12905.mo" "12905.p1" "12905.s1" "12933.fa" "12933.mo" "12933.p1" "13008.fa" "13008.mo" "13008.p1" "13031.fa" "13031.mo" "13031.p1" "13048.fa" "13048.mo" "13048.p1" "13048.s1" "13102.fa" "13102.mo" "13102.p1" "13116.fa" "13116.mo" "13116.p1" "13116.s1" "13158.fa" "13158.mo" "13158.p1" "13169.fa" "13169.mo" "13169.p1" "13169.s1" "13177.fa" "13177.mo" "13177.p1" "13188.fa" "13188.mo" "13188.p1" "13188.s1" "13207.fa" "13207.mo" "13207.p1" "13222.fa" "13222.mo" "13222.p1" "13274.fa" "13274.mo" "13274.p1" "13314.fa" "13314.mo" "13314.p1" "13333.fa" "13333.mo" "13333.p1" "13335.fa" "13335.mo" "13335.p1" "13335.s1" "13346.fa" "13346.mo" "13346.p1" "13346.s1" "13409.fa" "13409.mo" "13409.p1" "13415.fa" "13415.mo" "13415.p1" "13447.fa" "13447.mo" "13447.p1" "13447.s1" "13494.fa" "13494.mo" "13494.p1" "13517.fa" "13517.mo" "13517.p1" "13530.fa" "13530.mo" "13530.p1" "13532.fa" "13532.mo" "13532.p1" "13533.fa" "13533.mo" "13533.p1" "13533.s1" "13557.fa" "13557.mo" "13557.p1" "13593.fa" "13593.mo" "13593.p1" "13593.s1" "13606.fa" "13606.mo" "13606.p1" "13606.s1" "13610.fa" "13610.mo" "13610.p1" "13629.fa" "13629.mo" "13629.p1" "13629.s1" "13668.fa" "13668.mo" "13668.p1" "13678.fa" "13678.mo" "13678.p1" "13701.fa" "13701.mo" "13701.p1" "13726.fa" "13726.mo" "13726.p1" "13726.s1" "13733.fa" "13733.mo" "13733.p1" "13741.fa" "13741.mo" "13741.p1" "13742.fa" "13742.mo" "13742.p1" "13757.fa" "13757.mo" "13757.p1" "13793.fa" "13793.mo" "13793.p1" "13793.s1" "13798.fa" "13798.mo" "13798.p1" "13798.s1" "13812.fa" "13812.mo" "13812.p1" "13815.fa" "13815.mo" "13815.p1" "13815.s1" "13822.fa" "13822.mo" "13822.p1" "13835.fa" "13835.mo" "13835.p1" "13835.s1" "13844.fa" "13844.mo" "13844.p1" "13857.fa" "13857.mo" "13857.p1" "13863.fa" "13863.mo" "13863.p1" "13890.fa" "13890.mo" "13890.p1" "13890.s1" "13914.fa" "13914.mo" "13914.p1" "13926.fa" "13926.mo" "13926.p1" "13926.s1" "14006.fa" "14006.mo" "14006.p1" "14011.fa" "14011.mo" "14011.p1" "14011.s1" "14020.fa" "14020.mo" "14020.p1" "14201.fa" "14201.mo" "14201.p1" "14201.s1" "14292.fa" "14292.mo" "14292.p1"