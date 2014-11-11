#!/bin/sh
pid=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $5}'`
cpu_usage_ratio=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $3}'`
mem_usage_ratio=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $4}'`
mem_usage_value=`ps aux|grep ceilometer-agent-compute|grep -v grep|awk '{print $6}'`
time=`date`
transmit_bytes=`cat /proc/net/dev|grep eth0|awk '{print $9}'`
echo "$time $cpu_usage_ratio"
echo "$time $mem_usage_ratio"
echo "$time $mem_usage_value"
echo "$time $transmit_bytes"
