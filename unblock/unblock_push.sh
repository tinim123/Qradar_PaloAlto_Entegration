#!/bin/bash

############### Uniq Siralama Yapildi ########################
sort -u /root/soar/qradar_entegration/iplist.txt > /root/soar/qradar_entegration/unblock/uniq_iplist.txt
#:> unblock/for_unblock_iplist.txt
#for LINE in $(cat /root/soar/qradar_entegration/unblock/uniq_iplist.txt);
#do
#x=$(grep $LINE /root/soar/qradar_entegration/whitelist.txt)
#if [ ${#x} -gt 0 ]
#then
#echo  >/dev/null
#else
# echo $LINE >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.txt
#fi
#done

##############################################################
echo '<uid-message>' > /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '<type>update</type>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '  <payload>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '    <unregister>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
for LINE in $(cat /root/soar/qradar_entegration/unblock/uniq_iplist.txt);
do
echo '      <entry ip="'$LINE'" persistent="1">' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '        <tag>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '          <member>blacklist-ip-group</member>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '        </tag>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '      </entry>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
done
echo '    </unregister>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '  </payload>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml
echo '</uid-message>' >> /root/soar/qradar_entegration/unblock/for_unblock_iplist.xml

:>/root/soar/qradar_entegration/unblock/unblock_response.xml
############## Block IP Listesi Gonderiliyor ###################
curl -k -X POST 'https://x.x.x.x/api/?type=user-id&key=xxxxx' --data-urlencode cmd@/root/soar/qradar_entegration/unblock/for_unblock_iplist.xml -o /root/soar/qradar_entegration/unblock/unblock_response.xml
################################################################
