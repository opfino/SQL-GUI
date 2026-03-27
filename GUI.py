

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


def get_account_balance(account_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT BALANCE
            FROM ACCOUNT
            WHERE ACCOUNT_ID = :acc_id
            """,
            {"acc_id": account_id}
        )
        row = cursor.fetchone()
        return None if row is None else float(row[0])
    finally:
        cursor.close()
        conn.close()


def account_exists(account_id):
    return get_account_balance(account_id) is not None


def save_transaction_entry(transaction_id, from_account_id, to_account_id, transaction_date,
                           amount, trans_type, entry_date_text, create_both):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ---------------------------------------------
        # Validate source account
        # ---------------------------------------------
        from_balance = None
        if from_account_id != 0:
            cursor.execute(
                """
                SELECT BALANCE
                FROM ACCOUNT
                WHERE ACCOUNT_ID = :acc_id
                """,
                {"acc_id": from_account_id}
            )
            row = cursor.fetchone()
            if not row:
                raise Exception("From Account ID does not exist.")
            from_balance = float(row[0])

        # ---------------------------------------------
        # Deposit
        # ---------------------------------------------
        if trans_type == "Deposit":
            if from_account_id == 0:
                raise Exception("Account ID is required for deposit.")

            if create_both:
                cursor.execute(
                    '''
                    INSERT INTO TRANSACTIONS
                    (TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE, ACCOUNT_ID)
                    VALUES (:tid, :tdate, :amount, :ttype, :acc_id)
                    ''',
                    {
                        "tid": transaction_id,
                        "tdate": transaction_date,
                        "amount": amount,
                        "ttype": trans_type,
                        "acc_id": from_account_id
                    }
                )

            cursor.execute(
                """
                INSERT INTO TRANSACTIONENTRY
                (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT, ACCOUNT_ID, PROCESSED)
                VALUES (:tid, :tdate_txt, :ttype_num, :amount, :acc_id, 'N')
                """,
                {
                    "tid": transaction_id,
                    "tdate_txt": entry_date_text,
                    "ttype_num": 1,
                    "amount": amount,
                    "acc_id": from_account_id
                }
            )

        # ---------------------------------------------
        # Withdrawal
        # ---------------------------------------------
        elif trans_type == "Withdrawal":
            if from_account_id == 0:
                raise Exception("Account ID is required for withdrawal.")

            if from_balance < amount:
                raise Exception("Insufficient balance for withdrawal.")

            if create_both:
                cursor.execute(
                    '''
                    INSERT INTO TRANSACTIONS
                    (TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE, ACCOUNT_ID)
                    VALUES (:tid, :tdate, :amount, :ttype, :acc_id)
                    ''',
                    {
                        "tid": transaction_id,
                        "tdate": transaction_date,
                        "amount": amount,
                        "ttype": trans_type,
                        "acc_id": from_account_id
                    }
                )

            cursor.execute(
                """
                INSERT INTO TRANSACTIONENTRY
                (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT, ACCOUNT_ID, PROCESSED)
                VALUES (:tid, :tdate_txt, :ttype_num, :amount, :acc_id, 'N')
                """,
                {
                    "tid": transaction_id,
                    "tdate_txt": entry_date_text,
                    "ttype_num": 2,
                    "amount": amount,
                    "acc_id": from_account_id
                }
            )

        # ---------------------------------------------
        # Transfer
        # ---------------------------------------------
        elif trans_type == "Transfer":
            if from_account_id == 0:
                raise Exception("From Account ID is required for transfer.")
            if to_account_id == 0:
                raise Exception("To Account ID is required for transfer.")
            if from_account_id == to_account_id:
                raise Exception("From Account ID and To Account ID cannot be the same.")
            if from_balance < amount:
                raise Exception("Insufficient balance for transfer.")

            cursor.execute(
                """
                SELECT ACCOUNT_ID
                FROM ACCOUNT
                WHERE ACCOUNT_ID = :acc_id
                """,
                {"acc_id": to_account_id}
            )
            to_row = cursor.fetchone()
            if not to_row:
                raise Exception("To Account ID does not exist.")

            if create_both:
                cursor.execute(
                    '''
                    INSERT INTO TRANSACTIONS
                    (TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE, ACCOUNT_ID)
                    VALUES (:tid, :tdate, :amount, :ttype, :acc_id)
                    ''',
                    {
                        "tid": transaction_id,
                        "tdate": transaction_date,
                        "amount": amount,
                        "ttype": trans_type,
                        "acc_id": from_account_id
                    }
                )

            out_id = f"{transaction_id}_OUT"
            in_id = f"{transaction_id}_IN"

            # Outgoing entry from source account
            cursor.execute(
                """
                INSERT INTO TRANSACTIONENTRY
                (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT, ACCOUNT_ID, PROCESSED)
                VALUES (:tid, :tdate_txt, :ttype_num, :amount, :acc_id, 'N')
                """,
                {
                    "tid": out_id,
                    "tdate_txt": entry_date_text,
                    "ttype_num": 2,
                    "amount": amount,
                    "acc_id": from_account_id
                }
            )

            # Incoming entry to destination account
            cursor.execute(
                """
                INSERT INTO TRANSACTIONENTRY
                (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT, ACCOUNT_ID, PROCESSED)
                VALUES (:tid, :tdate_txt, :ttype_num, :amount, :acc_id, 'N')
                """,
                {
                    "tid": in_id,
                    "tdate_txt": entry_date_text,
                    "ttype_num": 1,
                    "amount": amount,
                    "acc_id": to_account_id
                }
            )

        # ---------------------------------------------
        # Other
        # ---------------------------------------------
        else:
            if from_account_id == 0:
                raise Exception("Account ID is required.")

            if create_both:
                cursor.execute(
                    '''
                    INSERT INTO TRANSACTIONS
                    (TRANSACTION_ID, DATE_OF_TRANSACTION, AMOUNT, TYPE, ACCOUNT_ID)
                    VALUES (:tid, :tdate, :amount, :ttype, :acc_id)
                    ''',
                    {
                        "tid": transaction_id,
                        "tdate": transaction_date,
                        "amount": amount,
                        "ttype": trans_type,
                        "acc_id": from_account_id
                    }
                )

            cursor.execute(
                """
                INSERT INTO TRANSACTIONENTRY
                (TRANSACTION_ID, TRANSACTION_DATE, TRANSACTION_TYPE, AMOUNT, ACCOUNT_ID, PROCESSED)
                VALUES (:tid, :tdate_txt, :ttype_num, :amount, :acc_id, 'N')
                """,
                {
                    "tid": transaction_id,
                    "tdate_txt": entry_date_text,
                    "ttype_num": 3,
                    "amount": amount,
                    "acc_id": from_account_id
                }
            )

        # ---------------------------------------------
        # Let Oracle procedure process the entry/entries
        # ---------------------------------------------

        
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
        "Transaction Entry",
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
        This GUI is built from your Oracle schema.

        Available features:
        - Deposit to an account
        - Withdraw from an account
        - Transfer between accounts
        - View account details
        - View account-specific transaction history
        - View raw table data
        """
    )

# =========================================================
# TRANSACTION ENTRY
# =========================================================
elif menu == "Transaction Entry":
    st.header("Enter Transaction Entry")

    col1, col2 = st.columns(2)

    with col1:
        transaction_id = st.text_input("Transaction ID", value="")
        from_account_id = st.number_input("From Account ID", min_value=0, step=1)
        transaction_date = st.date_input("Transaction Date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0, step=1.0)
        trans_type = st.selectbox("Transaction Type", ["Deposit", "Withdrawal", "Transfer", "Other"])

        if trans_type == "Transfer":
            to_account_id = st.number_input("To Account ID", min_value=0, step=1)
        else:
            to_account_id = 0

    with col2:
        entry_date_text = st.text_input("TransactionEntry Date (text)", value=str(date.today()))
        st.info("Deposit = + balance, Withdrawal = - balance, Transfer = move between two accounts")

    create_both = st.checkbox("Insert into both TRANSACTION and TRANSACTIONENTRY", value=True)

    if st.button("Save Transaction Entry"):
        if not transaction_id.strip():
            st.error("Transaction ID is required.")
        elif from_account_id == 0:
            st.error("From Account ID is required.")
        elif trans_type == "Transfer" and to_account_id == 0:
            st.error("To Account ID is required only for transfers.")
        else:
            try:
                save_transaction_entry(
                    transaction_id=transaction_id.strip(),
                    from_account_id=from_account_id,
                    to_account_id=to_account_id,
                    transaction_date=transaction_date,
                    amount=amount,
                    trans_type=trans_type,
                    entry_date_text=entry_date_text,
                    create_both=create_both
                )
                st.success("Transaction entry saved successfully.")

            except Exception as e:
                st.error(f"Error saving entry: {e}")

# =========================================================
# ACCOUNT STATEMENT
# =========================================================
elif menu == "Account Statement":
    st.header("Account Statement")

    st.subheader("Account Lookup")

    account_id = st.number_input("Enter Account ID", min_value=0, step=1, key="statement_account_id")

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

    st.subheader("Transactions for Selected Account")

    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", value=date(2024, 1, 1), key="from_date")
    with col2:
        to_date = st.date_input("To Date", value=date.today(), key="to_date")

    if st.button("Show Transactions"):
        try:
            df_trans = fetch_dataframe(
                '''
                SELECT te.TRANSACTION_ID,
                       te.ACCOUNT_ID,
                       te.TRANSACTION_DATE,
                       te.TRANSACTION_TYPE,
                       te.AMOUNT,
                       te.PROCESSED,
                       t.DATE_OF_TRANSACTION,
                       t.TYPE
                FROM TRANSACTIONENTRY te
                LEFT JOIN TRANSACTIONS t
                    ON te.TRANSACTION_ID = t.TRANSACTION_ID
                WHERE te.ACCOUNT_ID = :acc_id
                ORDER BY te.TRANSACTION_ID
                ''',
                {
                    "acc_id": account_id
                }
            )

            if df_trans.empty:
                st.info("No transactions found for that account.")
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
            "TRANSACTIONS",
            "ZIPCODES"
        ]
    )

    if st.button("Load Table"):
        try:
            query = f"SELECT * FROM {table_name}"
            df = fetch_dataframe(query)

            st.write(f"### {table_name}")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading table: {e}")
