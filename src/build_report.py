# Databricks notebook source
# Builds <catalog>.<schema>.sales_report: total sales per region.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "sales_dev")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

# overwriteSchema lets a new version add or remove columns in a table an older version created.
from pyspark.sql import functions as F

report = (
    spark.table(f"{catalog}.{schema}.orders")
    .groupBy("region")
    .agg(F.sum("amount").alias("total_amount"))
)
report.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog}.{schema}.sales_report")
display(report)
