#!/bin/sh
pid=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $5}'`
cpu_usage_ratio=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $3}'`
mem_usage_ratio=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $4}'`
mem_usage_value=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $6}'`
time=`date +%s`
transmit_bytes=`cat /proc/net/dev|grep eth0|awk '{print $9}'`
pre_transmit_bytes=`tail -n1 /tmp/network_traffic.log |awk '{print $2}'`
echo $pre_transmit_bytes
echo "$time $cpu_usage_ratio" >> /tmp/cpu_usage_ratio.log
echo "$time $mem_usage_ratio" >> /tmp/mem_usage_ratio.log
echo "$time $mem_usage_value" >> /tmp/mem_usage_value.log
if [ -z $pre_transmit_bytes ] 
then
	echo "no found previous transmit bytes value, use default value: 0"
	pre_transmit_bytes=0
fi

delta_transmit_bytes=`expr $transmit_bytes - $pre_transmit_bytes`
echo "$time $delta_transmit_bytes" >> /tmp/network_traffic.log

