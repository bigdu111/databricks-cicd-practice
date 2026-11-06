# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# Loads sample raw orders into <catalog>.<schema>.orders.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "sales_dev")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

# overwriteSchema lets a new version add or remove columns in a table an older version created.
from transforms import clean_amount, segment

raw_orders = [
    ("o1", "North", "$1,200.50"),
    ("o2", "South", "$300"),
    ("o3", "North", "$75.25"),
    ("o4", "West", "$2,010.00"),
    ("o5", "South", "$410.75"),
]
rows = [
    (order_id, region, clean_amount(amount), segment(clean_amount(amount)))
    for order_id, region, amount in raw_orders
]

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
df = spark.createDataFrame(rows, "order_id string, region string, amount double, segment string")
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog}.{schema}.orders")
print(f"Wrote {df.count()} orders to {catalog}.{schema}.orders")