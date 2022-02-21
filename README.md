# aws-exporter说明
aws-exporter功能是采集aws上服务监控数据，生成prometheus所需格式。

一、服务安装及启动
方式一：直接启动
```
python main.py -p 9091 -c defalut.yml
```

方式二：打包成可执行文件
```
pyinstaller -F main.py -n aws-exporter-v0.0.1
# 以下启动命令二选一，默认端口9091，默认配置文件取default.yml
./dist/aws-exporter-v0.0.1
./dist/aws-exporter-v0.0.1 -p 9091 -c defalut.yml
```


二、采集配置说明（default.yml）
```
# aws账号的ak sk，需要对各资源都是读权限
ak: xxx
sk: xxx

# 项目名，在每个指标前加上的前缀；默认为"ops"。因为公司有多个项目账号，为了区分指标
project: "ops"

# 采集现在到多久之前的时间数据，单位：秒，默认 60，必须为整数，最好60倍数，aws也有次参数要求，具体请参考aws文档
period: 60

# regions 建议哪个区，就放在哪个区对应的机器上采集，夸地区，特别是跨洲，延迟特别大；
regions:
  - us-west-2        # 俄勒冈
  - eu-central-1     # 法兰克福
  - ap-southeast-1   # 新加坡

# services对应aws上各种服务，集成服务包含如下
services:
  - ec2
  - elb
  - rds
  - redis
  - es
  - mq
  - kafka
  - s3

# 采集cloudwatch上的监控指标，只有service上配有的服务，这里配置才会采集;
# AmazonMQ： 队列相关指标，需要连接上实例，获取队列信息，然后查询cloudwatch api，侵入性太强，暂时没做；
# Kafka： topic相关指标，需要连接上实例，获取topic信息，然后查询cloudwatch api，侵入性太强，暂时没做；
metrics:
  # 配置示例Example，如果不明白，多用下aws cloudwatch即可
  AWS/EXAMPLE:             # aws namespace
    - name: metric_name    # aws metric name
      measure: 'SampleCount'|'Average'|'Sum'|'Minimum'|'Maximum'  # 结果指标类型，有5类可选取，默认Average
      period: 60           # 查找指标时间范围，默认60s
  
  # aws 实际配置，根据实际情况，自我修改
  # ec2实例多的时候，不建议在这里采集，因为网络太慢，建议使用zabbix
  AWS/EC2:
    - name: CPUUtilization
    - name: NetworkIn
    - name: NetworkOut
    - name: DiskReadOps
    - name: DiskWriteOps
    - name: StatusCheckFailed
  AWS/ELB:
    - name: RequestCount
      measure: Sum
    - name: UnHealthyHostCount
    - name: Latency
    - name: SurgeQueueLength
      measure: Maximum
  AWS/RDS:
    - name: CPUUtilization
    - name: DatabaseConnections
    - name: FreeableMemory
    - name: FreeStorageSpace
    - name: WriteIOPS
    - name: ReadIOPS
    - name: WriteLatency
    - name: ReadLatency
  AWS/ElastiCache:
    - name: CacheHitRate
    - name: CurrConnections
    - name: CPUUtilization
    - name: CPUCreditUsage
    - name: FreeableMemory
    - name: DatabaseMemoryUsagePercentage
    - name: NetworkBytesIn
    - name: NetworkBytesOut
    - name: ReplicationLag
  AWS/ES:
    - name: IndexingRate
    - name: IndexingLatency
    - name: SearchRate
    - name: SearchLatency
    - name: WriteIOPS
    - name: WriteLatency
    - name: ReadIOPS
    - name: ReadLatency
    - name: FreeStorageSpace
    - name: ClusterUsedSpace
    - name: ClusterStatus.green
  AWS/AmazonMQ:
    - name: CpuUtilization
    - name: NetworkIn
    - name: NetworkOut
    - name: StorePercentUsage
    - name: CurrentConnectionsCount
    - name: TotalMessageCount
    - name: TotalEnqueueCount
    - name: TotalDequeueCount
    - name: TotalProducerCount
    - name: TotalConsumerCount
  AWS/Kafka:
    - name: GlobalPartitionCount
    - name: GlobalTopicCount
    - name: ClientConnectionCount
    - name: KafkaDataLogsDiskUsed
    
#  未实现s3 metric，没有找到api
#  AWS/S3:
#    - name: BucketSizeBytes
#      period: 86400
#    - name: NumberOfObjects
#      period: 86400
```


三、强烈吐槽aws
1、aws sdk调用，返回太慢；建议采集部署，一个地区一个节点，跨区，太慢；建议不要采集ec2信息，调用次数太多，调用速度，让人崩溃；
2、aws cloudwatch调用，一个实例，一个指标只能调用一次，而阿里一种服务，一个指标调用一次，像ec2 elb实例多的服务，aws的的调用让人无奈，一方面调用次数多，费钱，另一方面，结果返回更慢，影响效率；
3、aws文档是真的多，但质量嘛，哈哈；
4、aws的客服，不行，一问三不知，让你自己查文档，阿里虽然吐槽也多，但东西就怕对比；