#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import lib
from datetime import datetime
import logging

from prometheus_client.core import GaugeMetricFamily

from cloud.aws import AWS


class AwsCollector(object):
    # metric命名规则：<project>_aws_<service>_<metric>_<statistic>  实例命名规则：<project>_aws_meta_<service>_info
    def __init__(self, client: AWS):
        self.client = client

    def collect(self):
        logging.info("collect action starting")

        self.client.set_end_time()  # 每次重新拉数据，设置当前时间为 查询数据的截止时间

        for service in self.client.services:
            if service == "ec2":
                instances = self.client.obtain_all_ec2()
            elif service == "elb":
                instances = self.client.obtain_all_elb()
            elif service == "rds":
                instances = self.client.obtain_all_rds()
            elif service == "redis":
                instances = self.client.obtain_all_redis()
            elif service == "es":
                instances = self.client.obtain_all_es()
            elif service == "mq":
                instances = self.client.obtain_all_mq()
            elif service == "kafka":
                instances = self.client.obtain_all_kafka()
            elif service == "s3":
                instances = self.client.obtain_s3()
            else:
                instances = []

            # 实例信息
            service_info = self.c_common_info(instances, service)
            if service_info:
                yield service_info
            # 指标数据
            metrics = self.c_common_metric(instances, service)
            for metric in metrics:
                yield metric

        logging.info("collect action end")

    def c_common_info(self, instances, service):
        if len(instances) == 0:
            return None
        metric_name = self.client.project + "_aws_meta_" + service.lower() + "_info"
        info_g = GaugeMetricFamily(name=metric_name, documentation="", labels=[key.replace(" ", "_") if " " in key else key for key in instances[0].keys()])
        for item in instances:
            info_g.add_metric(labels=item.values(), value=1)
        return info_g

    def c_common_metric(self, instances, service):
        res = list()
        if len(instances) == 0:
            return res

        namespace = "AWS/" + self.client.service_namespace[service]
        if namespace not in self.client.metrics.keys():  # 如果没有配置metrics指标，则不继续采集数据
            return res
        metrics = self.client.metrics[namespace]
        for metric in metrics:
            metric = self.client.config_metric(metric)  # 补全metric的默认配置

            # 创建GaugeMetricFamily
            metric_g = GaugeMetricFamily(
                name="%s_aws_%s_%s_%s" % (self.client.project, service, metric["name"].lower().replace(".", "_"), metric["measure"].lower()),
                documentation="",          # 原本写metric单位，奈何aws有些查询结果直接空，取不了单位
                labels=["instance_name"]
            )
            for index, instance in enumerate(instances):
                dimensions = list()  # cloudwatch上各个key及val的内容填充
                for item in self.client.service_cloudwatch_keys[service]:
                    dimension = dict()
                    dimension["Name"] = item
                    dimension["Value"] = instance[item]
                    dimensions.append(dimension)

                # 查询metric数据
                query = self.client.obtain_metric_datapoint(
                    region=instance["region"],
                    namespace=namespace,
                    metric_name=metric["name"],
                    start_time=self.client.get_start_time(metric["period"]),
                    end_time=self.client.end_time,
                    period=metric["period"],
                    dimensions=dimensions,
                    statistic=metric["measure"]
                )
                metric_g.add_metric(
                    labels=[instance["name"]],
                    value=0 if len(query) == 0 else query[0][metric["measure"]]
                )

            res.append(metric_g)
        return res
