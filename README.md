# Market Basket Analysis & Cross-Sell Recommendation Engine

A Streamlit-based data analytics and recommendation application that uses Market Basket Analysis, the Apriori Algorithm, Association Rules, and Time-Aware Recommendations to identify products that are frequently purchased together and generate cross-sell recommendations.

## Project Overview

This project analyzes retail transaction data to understand customer purchasing patterns and generate useful product recommendations.

The application provides different modules for data preparation, transformation, exploratory data analysis, market basket analysis, association rules, product recommendations, and time-aware recommendations.

## Key Features

- Data Preparation
- Data Transformation
- Exploratory Data Analysis (EDA)
- Sales Overview
- Dashboard
- Apriori Algorithm
- Frequent Itemset Generation
- Association Rule Mining
- Product Recommendations
- Bundle Creation
- Cross-Sell Recommendations
- Time-Aware Recommendations
- Best Time to Sell Analysis
- Recommendation History
- Streamlit User Interface

## Technologies Used

- Python
- Streamlit
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Apriori Algorithm
- Association Rule Mining
- SQL / Database Integration

## Project Workflow

1. Upload or provide retail transaction data.
2. Prepare and clean the data.
3. Transform the data into a suitable format.
4. Perform exploratory data analysis.
5. Generate frequent itemsets using the Apriori algorithm.
6. Generate association rules.
7. Analyze relationships between products.
8. Generate product and cross-sell recommendations.
9. Analyze time-based purchasing patterns.
10. Display the results through the Streamlit application.

## Project Structure

```text
Market-Basket-Cross-Sell-Engine/
│
├── app.py
├── config.py
├── db.py
├── helpers.py
├── pipeline.py
├── requirements.txt
├── sales_view.py
├── sidebar.py
├── state.py
├── theme.py
├── time_aware.py
├── README.md
│
├── views/
│   ├── __init__.py
│   ├── apriori_algorithm.py
│   ├── association_rules.py
│   ├── best_time_to_sell.py
│   ├── bundle_creation.py
│   ├── dashboard.py
│   ├── data_preparation.py
│   ├── data_transformation.py
│   ├── eda.py
│   ├── get_recommendations.py
│   ├── history.py
│   ├── home.py
│   ├── product_recommendation.py
│   ├── sales_overview.py
│   └── time_aware_recommendations.py
│
└── .streamlit/
