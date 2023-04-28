#!/bin/bash

############### Uniq Siralama Yapildi ########################
sort -u /root/soar/qradar_entegration/iplist.txt > /root/soar/qradar_entegration/block/uniq_iplist.txt
:> /root/soar/qradar_entegration/block/for_block_iplist.txt
for LINE in $(cat /root/soar/qradar_entegration/block/uniq_iplist.txt);
do
#x=$(grep $LINE /root/soar/qradar_entegration/whitelist.txt)
#if [ ${#x} -gt 0 ]
#then
# echo  >/dev/null
#else
echo $LINE > /root/soar/qradar_entegration/block/ip
a=$(grep -E '^(192\.168|10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|10\.)' /root/soar/qradar_entegration/block/ip)
if [ ${#a} -gt 0 ]
then
 echo  >/dev/null
else
 echo $LINE >> /root/soar/qradar_entegration/block/for_block_iplist.txt
fi
#fi
done
rm -rf /root/soar/qradar_entegration/block/ip
##############################################################
echo '<uid-message>' > /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '<type>update</type>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '  <payload>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '    <register>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
for LINE in $(cat /root/soar/qradar_entegration/block/for_block_iplist.txt);
do
echo '      <entry ip="'$LINE'" persistent="1">' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '        <tag>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '          <member>blacklist-ip-group</member>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '          <member timeout="259200">black-list-timeout</member>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '        </tag>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '      </entry>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
done
echo '    </register>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '  </payload>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml
echo '</uid-message>' >> /root/soar/qradar_entegration/block/for_block_iplist.xml

:> /root/soar/qradar_entegration/block/block_response.xml
############## Block IP Listesi Gonderiliyor ###################
curl -k -X POST 'https://xxx.xxx.xxx.xxx/api/?type=user-id&key=xxxxxxxxxxxxxxxxxxxxxx' --data-urlencode cmd@/root/soar/qradar_entegration/block/for_block_iplist.xml -o /root/soar/qradar_entegration/block/block_response.xml
################################################################

cat /root/soar/qradar_entegration/block/for_block_iplist.xml |grep ip= | cut -d"\"" -f2 > /root/soar/qradar_entegration/block/uniq_iplist.txt

