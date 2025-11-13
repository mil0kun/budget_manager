import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from sqlalchemy import text

# --- App Configuration ---
st.set_page_config(
    page_title="Personal Monthly Budget Manager",
    page_icon="💰",
    layout="wide",
)

# --- Database Connection (using st.connection and st.secrets) ---
# The connection details are stored in .streamlit/secrets.toml
# Example secrets.toml:
# [connections.db]
# url = "postgresql://user:password@host:port/dbname"

try:
    conn = st.connection("db", type="sql", pool_pre_ping=True)
except Exception as e:
    st.error(
        "Could not connect to the database. Please ensure your `secrets.toml` file is configured correctly."
    )
    st.stop()

# --- Database Initialization ---
@st.cache_resource
def init_db():
    """Create the transactions table if it doesn't exist."""
    with conn.session as s:
        s.execute(
            text("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                description TEXT
            );
            """)
        )
        s.commit()

init_db()

# --- Data Functions ---
def add_transaction(date, type, category, amount, description):
    """Adds a new transaction to the database."""
    with conn.session as s:
        s.execute(
            text("""
            INSERT INTO transactions (date, type, category, amount, description)
            VALUES (:date, :type, :category, :amount, :description)
            """),
            params=dict(
                date=date,
                type=type,
                category=category,
                amount=amount,
                description=description,
            ),
        )
        s.commit()
    st.cache_data.clear()
@st.cache_data
def get_all_transactions():
    """Retrieves all transactions from the database and returns a DataFrame."""
    df = conn.query("SELECT date, type, category, amount, description FROM transactions ORDER BY date DESC", ttl=0)
    df['date'] = pd.to_datetime(df['date'])
    return df

# --- Main App ---
st.title("💰 Personal Monthly Budget Manager")
st.markdown("Track your income and expenses with ease.")

# --- Input Form ---
with st.sidebar:
    st.header("Add a New Transaction")
    type_input = st.selectbox("Type", ["Income", "Expense"],placeholder="Please select a type")
    with st.form("transaction_form", clear_on_submit=True):
        date_input = st.date_input("Date", value=datetime.date.today())
        
        if type_input == "Income":
            categories = ["Salary", "Gift","Part-Time","Bonus investment", "Other"]
        else:
            categories = ["Food", "Investment", "Utilities", "Entertainment", "Transport", "shopping","Other"]
        
        category_input = st.selectbox("Category", categories)
        amount_input = st.number_input("Amount", min_value=0.01, format="%.2f" ,)
        description_input = st.text_area("Description (Optional)")
        
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            add_transaction(date_input, type_input, category_input, amount_input, description_input)
            st.success("Transaction added successfully!")

# --- Data Retrieval and Summary ---
transactions_df = get_all_transactions()

if transactions_df.empty:
    st.info("No transactions yet. Add one using the form on the left.")
else:
    total_income = transactions_df[transactions_df["type"] == "Income"]["amount"].sum()
    total_expenses = transactions_df[transactions_df["type"] == "Expense"]["amount"].sum()
    net_savings = total_income - total_expenses

    st.header("Budget Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${total_income:,.2f}")
    col2.metric("Total Expenses", f"${total_expenses:,.2f}")
    col3.metric("Net Savings", f"${net_savings:,.2f}", delta=f"{net_savings:,.2f}")

    # --- Data Visualization ---
    st.header("Visualizations")
    
    # Expense Category Breakdown
    expenses_df = transactions_df[transactions_df["type"] == "Expense"]
    if not expenses_df.empty:
        fig_pie = px.pie(
            expenses_df,
            names="category",
            values="amount",
            title="Expense Category Breakdown",
            hole=0.5,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')

        # Spending Over Time
        expenses_by_day = expenses_df.groupby(expenses_df['date'].dt.date)['amount'].sum().reset_index()
        fig_bar = px.bar(
            expenses_by_day,
            x="date",
            y="amount",
            title="Daily Expenses",
            labels={"date": "Date", "amount": "Total Expense"},
        )
        fig_bar.update_layout(xaxis_title="Date", yaxis_title="Amount ($)")
        
        viz_col1, viz_col2 = st.columns(2)
        with viz_col1:
            st.plotly_chart(fig_pie, width='stretch')
        with viz_col2:
            st.plotly_chart(fig_bar, width='stretch')
    else:
        st.info("No expenses recorded to visualize.")

    # --- Data Display ---
    st.header("Full Transaction History")
    st.dataframe(transactions_df, width='stretch')
