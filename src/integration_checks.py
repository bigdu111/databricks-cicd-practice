# Databricks notebook source
# Runs after each deploy to dev and test (Deploy to dev, Deploy to test), not in CI.
# Any failed assert fails the job, which fails the GitHub Actions run, so problems are
# caught before a release.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "sales_test")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

orders = spark.table(f"{catalog}.{schema}.orders")
report = spark.table(f"{catalog}.{schema}.sales_report")

assert orders.count() > 0, "orders table is empty"
assert report.count() > 0, "sales_report table is empty"

print(f"Integration checks passed for {catalog}.{schema}")
