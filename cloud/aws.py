#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import lib
import json
import copy
from datetime import datetime, timedelta

import boto3

from utils.tool import DateEncoder


class AWS(object):
    def __init__(self, ak="", sk="", project="ops", regions=[], period=60, services=[], metrics={}):
        self.ak = ak
        self.sk = sk
        self.project = project
        self.regions = regions
        self.period = period
        self.services = services
        self.metrics = metrics

        # 调用api获取metric时，传入的起始/截止时间
        self.start_time = None
        self.end_time = None

        # 默认参数
        self.service_cloudwatch_keys = {              # aws cloudwatch上，每个产品的name名称不一样，这里获取对应的name
            "ec2":   ["Instance name", "InstanceId"],
            "elb":   ["LoadBalancerName"],
            "rds":   ["DBInstanceIdentifier"],
            "redis": ["CacheClusterId"],
            "es":    ["DomainName", "ClientId"],
            "mq":    ["Broker"],
            "kafka": ["Cluster Name"],
            "s3":    ["BucketName"]
        }
        self.service_namespace = {   # key为服务缩写，val为aws上服务的名称，cloudwatch上namespace需要用;
            "ec2":   "EC2",
            "elb":   "ELB",
            "rds":   "RDS",
            "redis": "ElastiCache",
            "es":    "ES",
            "mq":    "AmazonMQ",
            "kafka": "Kafka",
            "s3":    "S3",
        }
        self.measure = "Average"            # 默认采集数据

    # 设置aws区域
    def set_region(self, region):
        boto3.setup_default_session(aws_access_key_id=self.ak, aws_secret_access_key=self.sk, region_name=region)

    # 传入metric参数，匹配没有的参数，用默认参数补充，拼成key都有的一个metric（后续参数也继续往这里加）.
    def config_metric(self, metric):
        if "measure" not in metric.keys():
            metric["measure"] = self.measure
        if "period" not in metric.keys():
            metric["period"] = self.period
        return metric

    def obtain_ec2(self, region):
        self.set_region(region)

        ec2s = list()

        c = boto3.client("ec2")
        instances = c.describe_instances()["Reservations"]
        for item in instances:
            ec2 = dict()
            instance = item["Instances"][0]

            name = ""
            for tag in instance["Tags"]:
                if tag["Key"] == "Name":
                    name = tag["Value"]
            ec2["name"] = name

            ec2["Instance name"] = name
            ec2["region"] = region
            ec2["image_id"] = instance["ImageId"]
            ec2["instance_id"] = instance["InstanceId"]
            ec2["InstanceId"] = instance["InstanceId"]
            ec2["type"] = instance["InstanceType"]
            ec2["zone"] = instance["Placement"]["AvailabilityZone"]
            ec2["private_ip"] = instance["PrivateIpAddress"]
            ec2["public_ip"] = instance["PublicIpAddress"] if "PublicIpAddress" in instance.keys() else ""
            ec2["state"] = instance["State"]["Name"]
            ec2["subnet_id"] = instance["SubnetId"]
            ec2["vpc_id"] = instance["VpcId"]
            ec2["architecture"] = instance["Architecture"]
            ec2["cpu_num"] = str(instance["CpuOptions"]["CoreCount"])
            ec2["platform"] = instance["PlatformDetails"]
            ec2s.append(ec2)
        return ec2s

    def obtain_all_ec2(self):
        ec2s = list()
        for region in self.regions:
            ec2s += self.obtain_ec2(region)
        with open("logs/aws-ec2.log", "w") as f:
            f.write(json.dumps(ec2s, indent=4, cls=DateEncoder))
        return ec2s

    def obtain_elb(self, region):
        self.set_region(region)

        elbs = list()

        c = boto3.client("elb")  # classic elb
        classic_elb = c.describe_load_balancers()["LoadBalancerDescriptions"]
        for item in classic_elb:
            elb = dict()
            elb["name"] = item["LoadBalancerName"]
            elb["LoadBalancerName"] = item["LoadBalancerName"]
            elb["region"] = region
            elb["type"] = "classic"
            if item["Scheme"] == "internet-facing":
                elb["network"] = "outer"
            else:
                elb["network"] = "inner"
            elbs.append(elb)

        c = boto3.client("elbv2")  # network | application elb
        network_elb = c.describe_load_balancers()["LoadBalancers"]
        for item in network_elb:
            elb = dict()
            elb["name"] = item["LoadBalancerName"]
            elb["LoadBalancerName"] = item["LoadBalancerName"]
            elb["region"] = region
            elb["type"] = item["Type"]
            if item["Scheme"] == "internet-facing":
                elb["network"] = "outer"
            else:
                elb["network"] = "inner"
            elbs.append(elb)

        return elbs

    def obtain_all_elb(self):
        elbs = list()
        for region in self.regions:
            elbs += self.obtain_elb(region)
        with open("logs/aws-elb.log", "w") as f:
            f.write(json.dumps(elbs, indent=4, cls=DateEncoder))
        return elbs

    def obtain_rds(self, region):
        self.set_region(region)

        res = list()

        c = boto3.client("rds")
        aws_rds = c.describe_db_instances()["DBInstances"]
        for item in aws_rds:
            rds = dict()
            rds["name"] = item["DBInstanceIdentifier"]
            rds["DBInstanceIdentifier"] = item["DBInstanceIdentifier"]
            rds["region"] = region
            rds["type"] = item["DBInstanceClass"]
            rds["engine"] = item["Engine"]
            rds["version"] = item["EngineVersion"]
            rds["storage_type"] = item["StorageType"]
            rds["storage_used"] = str(item["AllocatedStorage"])    # prometheus对维度值，只能用字符串
            if "MaxAllocatedStorage" in item.keys():
                rds["storage_size"] = str(item["MaxAllocatedStorage"])
            else:
                rds["storage_size"] = "0"  # 0表示磁盘大小会自动扩的，没有磁盘大小限制

            res.append(rds)
        return res

    def obtain_all_rds(self):
        rdses = list()
        for region in self.regions:
            rdses += self.obtain_rds(region)
        with open("logs/aws-rds.log", "w") as f:
            f.write(json.dumps(rdses, indent=4, cls=DateEncoder))
        return rdses

    def obtain_redis(self, region):
        self.set_region(region)

        res = list()

        c = boto3.client("elasticache")
        aws_redis = c.describe_cache_clusters()["CacheClusters"]
        for item in aws_redis:
            redis = dict()
            redis["name"] = item["CacheClusterId"]
            redis["CacheClusterId"] = item["CacheClusterId"]
            redis["region"] = region
            redis["type"] = item["CacheNodeType"]
            redis["engine"] = item["Engine"]
            redis["version"] = item["EngineVersion"]

            res.append(redis)
        return res

    def obtain_all_redis(self):
        redises = list()
        for region in self.regions:
            redises += self.obtain_redis(region)
        with open("logs/aws-redis.log", "w") as f:
            f.write(json.dumps(redises, indent=4, cls=DateEncoder))
        return redises

    def obtain_es(self, region):
        self.set_region(region)

        res = list()

        c = boto3.client("opensearch")
        opensearch_os = c.list_domain_names(EngineType='OpenSearch')["DomainNames"]
        opensearch_es = c.list_domain_names(EngineType='Elasticsearch')["DomainNames"]
        aws_opensearch = opensearch_os + opensearch_es
        for item in aws_opensearch:
            es = dict()
            domain = c.describe_domain(DomainName=item["DomainName"])["DomainStatus"]
            es["name"] = item["DomainName"]
            es["DomainName"] = item["DomainName"]
            es["ClientId"] = domain["DomainId"].split("/")[0]
            es["region"] = region
            es["engine"] = item["EngineType"]
            es["version"] = domain["EngineVersion"]
            es["type"] = domain["ClusterConfig"]["InstanceType"]
            es["storage_type"] = domain["EBSOptions"]["VolumeType"]
            es["storage_size"] = str(domain["EBSOptions"]["VolumeSize"])

            res.append(es)
        return res

    def obtain_all_es(self):
        es = list()
        for region in self.regions:
            es += self.obtain_es(region)
        with open("logs/aws-es.log", "w") as f:
            f.write(json.dumps(es, indent=4, cls=DateEncoder))
        return es

    def obtain_mq(self, region):
        self.set_region(region)
        res = list()

        c = boto3.client("mq")
        aws_mq_brokers = c.list_brokers()["BrokerSummaries"]
        for broker in aws_mq_brokers:
            mq = dict()
            aws_broker = c.describe_broker(BrokerId=broker["BrokerId"])
            mq["name"] = aws_broker["BrokerName"]
            mq["region"] = region
            mq["type"] = aws_broker["HostInstanceType"]
            mq["engine"] = aws_broker["EngineType"]
            mq["version"] = aws_broker["EngineVersion"]
            mq["storage_type"] = aws_broker["StorageType"]
            mq["broker_arn"] = aws_broker["BrokerArn"]
            for index in range(len(aws_broker["BrokerInstances"])):
                new_mq = copy.deepcopy(mq)
                new_mq["Broker"] = aws_broker["BrokerName"] + "-" + str(index+1)
                res.append(new_mq)
        return res

    def obtain_all_mq(self):
        mqs = list()
        for region in self.regions:
            mqs += self.obtain_mq(region)
        with open("logs/aws-mq.log", "w") as f:
            f.write(json.dumps(mqs, indent=4, cls=DateEncoder))
        return mqs

    def obtain_kafka(self, region):
        self.set_region(region)

        res = list()

        c = boto3.client("kafka")
        aws_kafka = c.list_clusters()["ClusterInfoList"]
        for item in aws_kafka:
            kafka = dict()
            kafka["name"] = item["ClusterName"]
            kafka["Cluster Name"] = item["ClusterName"]
            kafka["region"] = region
            kafka["type"] = item["BrokerNodeGroupInfo"]["InstanceType"]
            kafka["cluster_arn"] = item["ClusterArn"]
            kafka["zk_conn_str"] = item["ZookeeperConnectString"]
            kafka["version"] = item["CurrentBrokerSoftwareInfo"]["KafkaVersion"]
            kafka["num_of_broker_node"] = str(item["NumberOfBrokerNodes"])

            res.append(kafka)
        return res

    def obtain_all_kafka(self):
        kafkas = list()
        for region in self.regions:
            kafkas += self.obtain_kafka(region)
        with open("logs/aws-kafka.log", "w") as f:
            f.write(json.dumps(kafkas, indent=4, cls=DateEncoder))
        return kafkas

    def obtain_s3(self):
        boto3.setup_default_session(aws_access_key_id=self.ak, aws_secret_access_key=self.sk)
        res = list()

        c = boto3.client("s3")
        buckets = c.list_buckets()["Buckets"]
        for item in buckets:
            bucket = dict()
            bucket["name"] = item["Name"]
            bucket["BucketName"] = item["Name"]
            region = c.get_bucket_location(Bucket=item["Name"])["LocationConstraint"]
            bucket["region"] = region if region else "us-east-1"   # aws问题，弗吉尼亚区，返回就是None，所以要人为添加

            res.append(bucket)
        with open("logs/aws-s3.log", "w") as f:
            f.write(json.dumps(res, indent=4, cls=DateEncoder))
        return res

    def obtain_metric_datapoint(self, region, namespace, metric_name, start_time, end_time, period, dimensions, statistic):
        # 获取一个区域内，根据metric名称，获取该实例时间区间内的监控值
        self.set_region(region)
        c = boto3.client('cloudwatch')

        return c.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )["Datapoints"]

    def get_start_time(self, period):
        return self.end_time - timedelta(seconds=period)

    def set_end_time(self):
        self.end_time = datetime.utcnow()
