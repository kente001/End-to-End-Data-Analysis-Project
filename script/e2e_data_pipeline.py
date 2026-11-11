End-to-End Data Analysis Pipeline
----------------------------------------
This script connects to a PostgreSQL database, loads data from multiple tables,
cleans and fixes invalid values, anonymizes sensitive information, merges data,
and creates derived columns for analysis.

Steps:
1. Connect to PostgreSQL database
2. Load tables: sales, products, salespersons, customers
3. Clean sales data (remove invalid rows, fix prices and costs)
4. Anonymize names and categories
5. Merge all tables into one dataset
6. Add derived fields (order_year, order_month, profit)
7. Save the cleaned data to CSV


import pandas as pd
from sqlalchemy import create_engine
from faker import Faker

# ---------------------------
# 1. Database Connection
# ---------------------------

engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

# ---------------------------
# 2. Load Data
# ---------------------------
sales = pd.read_sql("SELECT * FROM sales", engine)
products = pd.read_sql("SELECT * FROM prod", engine)
salespersons = pd.read_sql("SELECT * FROM salespersons", engine)
customers = pd.read_sql("SELECT * FROM cust", engine)

# ---------------------------
# 3. Clean Sales Data
# ---------------------------
# Remove rows with invalid sales amount or quantity
sales = sales[(sales['sales_amount'] > 0) & (sales['sales_qty'] >= 1)]

# Fix unit_price < unit_cost issue
mask_invalid_price = sales['unit_price'] < sales['unit_cost']
median_margin = ((sales['unit_price'] - sales['unit_cost']) / sales['unit_cost']).median()
sales.loc[mask_invalid_price, 'unit_price'] = sales.loc[mask_invalid_price, 'unit_cost'] * (1 + median_margin)

# Estimate missing or zero costs
mask_missing_cost = (sales['unit_cost'] == 0) | (sales['unit_cost'].isnull())
sales.loc[mask_missing_cost, 'unit_cost'] = sales.loc[mask_missing_cost, 'unit_price'] * (1 - median_margin)

# ---------------------------
# 4. Anonymize Sensitive Data
# ---------------------------
fake = Faker()

# Anonymize product categories and names
products['product_category'] = products['prod_category'].rank(method='dense').astype(int).apply(lambda x: f'Category_{x}')
products['product_name'] = products.groupby('prod_category').cumcount() + 1
products['product_name'] = products['product_name'].apply(lambda x: f'Product_{x}')

# Anonymize salesperson names
salespersons['salesperson_name'] = [fake.name() for _ in range(len(salespersons))]

# Anonymize customer names
customers['cust_name'] = [fake.name() for _ in range(len(customers))]

# ---------------------------
# 5. Merge Data
# ---------------------------
merged = sales.merge(products[['prod_s_key', 'product_name', 'product_category']], on='prod_s_key', how='left')
merged = merged.merge(salespersons[['salesperson_s_key', 'salesperson_name', 'salesperson_type']], on='salesperson_s_key', how='left')
merged = merged.merge(customers[['cust_s_key', 'cust_name']], on='cust_s_key', how='left')

# Drop unnecessary keys
merged = merged.drop(columns=['prod_s_key', 'salesperson_s_key', 'sales_s_key', 'cust_s_key', 'sales_measure'])

# ---------------------------
# 6. Add Derived Fields
# ---------------------------
merged['order_date'] = pd.to_datetime(merged['order_date'])
merged['order_year'] = merged['order_date'].dt.year
merged['order_month'] = merged['order_date'].dt.strftime('%b-%Y')
merged['profit'] = (merged['unit_price'] - merged['unit_cost']) * merged['sales_qty']

# ---------------------------
# 7. Save Cleaned Data
# ---------------------------
merged.to_csv('cleaned_sales_data.csv', index=False)

