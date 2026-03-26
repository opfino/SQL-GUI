

import streamlit as st
import pandas as pd
import oracledb
from datetime import date

# =========================================================
# DATABASE SETTINGS
# =========================================================
HOST = "192.168.9.87"
PORT = 1521
SERVICE_NAME = "XEPDB1"
USERNAME = "banki"
PASSWORD = "password"


# =========================================================
# DATABASE CONNECTION
# =========================================================
def get_connection():
    dsn = oracledb.makedsn(HOST, PORT, service_name=SERVICE_NAME)
    return oracledb.connect(
        user=USERNAME,
        password=PASSWORD,
        dsn=dsn
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def fetch_dataframe(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params or {})
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
    finally:
        cursor.close()
        conn.close()


def execute_dml(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params or {})
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def save_journal_entry(transaction_id, transaction_date, amount, trans_type,
                       entry_date_text, entry_type_num, create_both):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if create_both:
            cursor.execute(
                '''
                INSERT INTO "TRANSACTION"
                (TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE)
                VALUES (:tid, :tdate, :amount, :ttype)
                ''',
                {
                    "tid": transaction_id,
                    "tdate": transaction_date,
                    "amount": amount,
                    "ttype": trans_type
                }
            )

        cursor.execute(
            """
            INSERT INTO TRANSACTIONENTRY
            (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT)
            VALUES (:tid, :tdate_txt, :ttype_num, :amount)
            """,
            {
                "tid": transaction_id,
                "tdate_txt": entry_date_text,
                "ttype_num": entry_type_num,
                "amount": amount
            }
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(page_title="Banking GUI", layout="wide")
st.title("Banking System GUI")

menu = st.sidebar.radio(
    "Choose page",
    [
        "Home",
        "Journal Entry",
        "Account Statement",
        "View Tables"
    ]
)

# =========================================================
# HOME
# =========================================================
if menu == "Home":
    st.header("Welcome")
    st.write(
        """
        This GUI is built from your current Oracle schema.

        Available features:
        - Enter journal entries
        - View accounts
        - View transactions
        - View account table data

        Note:
        Your current schema does not link transactions directly to accounts,
        so the account statement page can show account info and transaction info,
        but not a perfect transaction-per-account statement.
        """
    )

# =========================================================
# JOURNAL ENTRY
# =========================================================
elif menu == "Journal Entry":
    st.header("Enter Journal Entry")

    col1, col2 = st.columns(2)

    with col1:
        transaction_id = st.text_input("Transaction ID", value="")
        transaction_date = st.date_input("Transaction Date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0, step=1.0)
        trans_type = st.selectbox("Transaction Type", ["Deposit", "Withdrawal", "Transfer", "Other"])

    with col2:
        entry_date_text = st.text_input("TransactionEntry Date (text)", value=str(date.today()))
        entry_type_num = st.number_input("TransactionEntry Type Number", min_value=1, step=1)
        st.info("Example: 1 = Deposit, 2 = Withdrawal, 3 = Transfer")

    create_both = st.checkbox("Insert into both TRANSACTION and TRANSACTIONENTRY", value=True)

    if st.button("Save Journal Entry"):
        if not transaction_id.strip():
            st.error("Transaction ID is required.")
        else:
            try:
                save_journal_entry(
                    transaction_id=transaction_id.strip(),
                    transaction_date=transaction_date,
                    amount=amount,
                    trans_type=trans_type,
                    entry_date_text=entry_date_text,
                    entry_type_num=entry_type_num,
                    create_both=create_both
                )
                st.success("Journal entry saved successfully.")

            except Exception as e:
                st.error(f"Error saving entry: {e}")

# =========================================================
# ACCOUNT STATEMENT
# =========================================================
elif menu == "Account Statement":
    st.header("Account Statement")

    st.subheader("Account Lookup")

    account_id = st.number_input("Enter Account ID", min_value=0, step=1)

    if st.button("Show Account"):
        try:
            df_account = fetch_dataframe(
                """
                SELECT ACCOUNT_ID, ESTABLISH_DATE, BALANCE
                FROM ACCOUNT
                WHERE ACCOUNT_ID = :acc_id
                """,
                {"acc_id": account_id}
            )

            if df_account.empty:
                st.warning("No account found with that Account ID.")
            else:
                st.write("### Account Details")
                st.dataframe(df_account, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading account: {e}")

    st.divider()

    st.subheader("All Transactions")
    st.write("Because the current schema has no ACCOUNT_ID inside TRANSACTIONENTRY, transactions cannot be filtered by account correctly.")

    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", value=date(2024, 1, 1), key="from_date")
    with col2:
        to_date = st.date_input("To Date", value=date.today(), key="to_date")

    if st.button("Show Transactions"):
        try:
            df_trans = fetch_dataframe(
                '''
                SELECT TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE
                FROM "TRANSACTION"
                WHERE DATE_OF_TRANSACTION BETWEEN :from_d AND :to_d
                ORDER BY DATE_OF_TRANSACTION, TRANSACTION_ID
                ''',
                {
                    "from_d": from_date,
                    "to_d": to_date
                }
            )

            if df_trans.empty:
                st.info("No transactions found in that date range.")
            else:
                st.write("### Transactions")
                st.dataframe(df_trans, use_container_width=True)

                st.write("### Summary")
                total_amount = df_trans["AMOUNT"].sum()
                st.metric("Total Amount", f"{total_amount}")

        except Exception as e:
            st.error(f"Error loading transactions: {e}")

# =========================================================
# VIEW TABLES
# =========================================================
elif menu == "View Tables":
    st.header("View Tables")

    table_name = st.selectbox(
        "Choose table",
        [
            "ACCESS_LEVEL",
            "ACCOUNT",
            "ACCOUNTTYPE",
            "BANK",
            "BRANCH",
            "CUSTOMER",
            "PERSON",
            "EMPLOYEE",
            "TRANSACTIONENTRY",
            "TRANSACTION",
            "ZIPCODES"
        ]
    )

    if st.button("Load Table"):
        try:
            if table_name == "TRANSACTION":
                query = 'SELECT * FROM "TRANSACTION"'
            else:
                query = f"SELECT * FROM {table_name}"

            df = fetch_dataframe(query)

            st.write(f"### {table_name}")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading table: {e}")