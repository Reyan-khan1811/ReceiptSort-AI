import os
import json
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# =============== PAGE CONFIG ===============
st.set_page_config(
    page_title="ReceiptSort AI",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============== BEIGE + EMERALD THEME ===============
st.markdown("""
<style>
:root {
    --beige: #F4EFE5;
    --emerald: #087F5B;
    --forest: #173D30;
    --sage: #DCEFE5;
    --cream: #FFFCF6;
    --muted: #718075;
    --border: #E4DED1;
}

.stApp {
    background: #F4EFE5;
    color: #173D30;
}

[data-testid="stHeader"] {
    background: rgba(244,239,229,0.95);
}

[data-testid="stSidebar"] {
    background: #E7DDCB;
    border-right: 1px solid #D8CEBD;
}

h1, h2, h3, h4 {
    color: #173D30 !important;
}

p, label, .stMarkdown {
    color: #315C49;
}

[data-testid="stMetric"] {
    background: #FFFCF6;
    border: 1px solid #E4DED1;
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 3px 12px rgba(23,61,48,0.04);
}

[data-testid="stMetricLabel"] {
    color: #718075 !important;
}

[data-testid="stMetricValue"] {
    color: #173D30 !important;
    font-weight: 750;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: #087F5B;
    color: white;
    border: 1px solid #087F5B;
    border-radius: 10px;
    font-weight: 650;
    transition: 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: #066A4B;
    color: white;
    border-color: #066A4B;
}

/* Fix dark input fields and unreadable text */
[data-testid="stDateInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: #FFFCF6 !important;
    color: #173D30 !important;
    -webkit-text-fill-color: #173D30 !important;
    border-color: #D8CEBD !important;
}

/* Dropdowns: category, currency, payment method */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: #FFFCF6 !important;
    border-color: #D8CEBD !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] * {
    color: #173D30 !important;
    -webkit-text-fill-color: #173D30 !important;
}

/* Save and submit buttons */
[data-testid="stFormSubmitButton"] button {
    color: #FFFCF6 !important;
}
input, textarea {
    color: #173D30 !important;
}

[data-testid="stFileUploader"] {
    background: #FFFCF6;
    border: 1px dashed #9CBBAA;
    border-radius: 14px;
    padding: 12px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #E4DED1;
    border-radius: 12px;
}

.hero {
    background: linear-gradient(120deg, #FFFCF6, #E5F1E8);
    border: 1px solid #D9E5D9;
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 22px;
}

.hero-kicker {
    color: #087F5B;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.hero-title {
    color: #173D30;
    font-size: 38px;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 8px;
}

.hero-copy {
    color: #526C5D;
    font-size: 16px;
    margin-bottom: 0;
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}


/* Only the Expense details form */
div[data-testid="stForm"]:has(button) {
    background: #000000 !important;
    border: 1px solid #333333 !important;
    border-radius: 14px !important;
    padding: 20px !important;
}

/* White labels */
div[data-testid="stForm"] label,
div[data-testid="stForm"] p {
    color: #FFFFFF !important;
}

/* Black input boxes with white text */
div[data-testid="stForm"] input,
div[data-testid="stForm"] textarea,
div[data-testid="stForm"] [data-baseweb="select"] > div {
    background: #1A1A1A !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border-color: #555555 !important;
}

/* Save button */
div[data-testid="stForm"] button {
    background: #087F5B !important;
    color: #FFFFFF !important;
}

</style>
""", unsafe_allow_html=True)


# =============== CONSTANTS ===============
CATEGORIES = [
    "Food & groceries",
    "Transport",
    "Shopping",
    "Bills & utilities",
    "Software & subscriptions",
    "Education",
    "Health",
    "Travel",
    "Office & supplies",
    "Other",
]

COLUMNS = [
    "Date",
    "Merchant",
    "Category",
    "Description",
    "Amount",
    "Currency",
    "Payment method",
    "Receipt filename",
]


# =============== HELPER FUNCTIONS ===============
def empty_expenses():
    return pd.DataFrame(columns=COLUMNS)


def money(amount, currency="INR"):
    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
    }

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0.0

    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def extract_receipt(image_bytes):
    """Use a configured Gemma model to extract receipt details."""
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or st.session_state.get("api_key", "")
    )

    if not api_key:
        return None, "Add your Google AI API key in Settings to enable AI extraction."

    if genai is None:
        return None, "Install the AI package using: pip install google-genai"

    try:
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMMA_MODEL", "gemini-3.5-flash-lite")

        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        prompt = """
        Read the receipt and return ONLY valid JSON with these fields:
        {
          "date": "YYYY-MM-DD or empty string",
          "merchant": "store name",
          "category": "one of the provided categories",
          "description": "short description",
          "amount": 0.0,
          "currency": "INR",
          "payment_method": "UPI, Card, Cash, or Unknown"
        }

        Categories:
        Food & groceries, Transport, Shopping, Bills & utilities,
        Software & subscriptions, Education, Health, Travel,
        Office & supplies, Other.

        Do not invent unreadable details. The amount should be the
        final total paid, not the subtotal, when clearly available.
        """

        response = client.models.generate_content(
            model=model,
            contents=[prompt, image],
            config=types.GenerateContentConfig(temperature=0.1),
        )

        raw = (response.text or "").strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]

        return json.loads(raw), None

    except Exception as error:
        return None, f"Extraction failed: {error}"


# =============== SESSION STATE ===============
if "expenses" not in st.session_state:
    st.session_state.expenses = empty_expenses()

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "extracted" not in st.session_state:
    st.session_state.extracted = {}

if "receipt_name" not in st.session_state:
    st.session_state.receipt_name = ""

if "receipt_bytes" not in st.session_state:
    st.session_state.receipt_bytes = None
    # =============== SIDEBAR ===============

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 12px 0 18px 0;">
            <div style="
                background: #087F5B;
                color: white;
                width: 48px;
                height: 48px;
                border-radius: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 25px;
                margin-bottom: 14px;">
                🧾
            </div>
            <h2 style="
                color: #173D30;
                margin: 0;
                font-size: 25px;">
                ReceiptSort AI
            </h2>
            <p style="
                color: #718075;
                font-size: 13px;
                margin-top: 6px;">
                Your calm, organized expense space
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='color:#718075;font-size:11px;"
        "font-weight:700;letter-spacing:2px;'>NAVIGATION</p>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Add receipt",
            "Expense history",
            "Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    palette_html = """
    <div style="display:flex;gap:8px;">
        <div style="flex:1;text-align:center;">
            <div style="height:30px;background:#F4EFE5;border:1px solid #E4DED1;border-radius:8px;"></div>
            <div style="color:#718075;font-size:10px;margin-top:5px;">Beige</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="height:30px;background:#087F5B;border:1px solid #E4DED1;border-radius:8px;"></div>
            <div style="color:#718075;font-size:10px;margin-top:5px;">Emerald</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="height:30px;background:#173D30;border:1px solid #E4DED1;border-radius:8px;"></div>
            <div style="color:#718075;font-size:10px;margin-top:5px;">Forest</div>
        </div>
    """




    st.divider()
    
    st.markdown(
        "<p style='color:#718075;font-size:11px;"
        "font-weight:700;letter-spacing:2px;'>COLOR PALETTE</p>",
        unsafe_allow_html=True,
    )

    palette_html = """
    <div style="display:flex;gap:10px;margin:8px 0 14px 0;">
        <div style="flex:1;text-align:center;">
            <div style="height:28px;background:#F4EFE5;border:1px solid #D8D0C2;border-radius:7px;"></div>
            <div style="font-size:10px;color:#718075;margin-top:5px;">Beige</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="height:28px;background:#087F5B;border-radius:7px;"></div>
            <div style="font-size:10px;color:#718075;margin-top:5px;">Emerald</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="height:28px;background:#173D30;border-radius:7px;"></div>
            <div style="font-size:10px;color:#718075;margin-top:5px;">Forest</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="height:28px;background:#DCEFE5;border:1px solid #D8D0C2;border-radius:7px;"></div>
            <div style="font-size:10px;color:#718075;margin-top:5px;">Sage</div>
        </div>
    </div>
    """

    st.markdown(palette_html, unsafe_allow_html=True)


    st.divider()
    st.caption("Track expenses. Keep receipts organized. Export anytime.")


# =============== OVERVIEW ===============
if page == "Overview":

    st.markdown("""
    <div class="hero">
        <div class="hero-kicker">Expense clarity, made simple</div>
        <div class="hero-title">Your money, neatly sorted.</div>
        <p class="hero-copy">
            Upload receipts, organize expenses, and understand
            your spending in one simple workspace.
        </p>
    </div>
    """, unsafe_allow_html=True)

    expenses = st.session_state.expenses.copy()

    if not expenses.empty:
        expenses["Amount"] = pd.to_numeric(
            expenses["Amount"], errors="coerce"
        ).fillna(0)

        total = expenses["Amount"].sum()
        count = len(expenses)
        average = total / count if count else 0
        currency = str(expenses.iloc[-1]["Currency"] or "INR")
    else:
        total = 0
        count = 0
        average = 0
        currency = "INR"

    col1, col2, col3 = st.columns(3)

    col1.metric("Total tracked", money(total, currency))
    col2.metric("Expenses recorded", count)
    col3.metric("Average expense", money(average, currency))

    st.write("")

    left, right = st.columns([1.2, 0.8], gap="large")

    with left:
        st.subheader("Recent expenses")

        if expenses.empty:
            st.info(
                "No expenses yet. Add your first receipt to get started."
            )

            if st.button("＋ Add your first receipt", width="stretch"):
                st.session_state["go_to_add"] = True
                st.rerun()

        else:
            recent = expenses.tail(6).iloc[::-1]

            st.dataframe(
                recent[
                    ["Date", "Merchant", "Category", "Amount", "Currency"]
                ],
                width="stretch",
                hide_index=True,
            )

    with right:
        st.subheader("Spending by category")

        if expenses.empty:
            st.markdown("""
            <div style="background:#FFFCF6;border:1px solid #E4DED1;
                        padding:24px;border-radius:16px">
                <div style="font-size:32px">🌿</div>
                <b style="color:#173D30">Your spending overview</b>
                <p style="color:#718075">
                    Category insights will appear when you add expenses.
                </p>
            </div>
            """, unsafe_allow_html=True)

        else:
            category_totals = (
                expenses.groupby("Category")["Amount"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(category_totals)

    if not expenses.empty:
        st.subheader("Monthly trend")

        dated = expenses.copy()
        dated["Date"] = pd.to_datetime(
            dated["Date"], errors="coerce"
        )
        dated = dated.dropna(subset=["Date"])

        if not dated.empty:
            dated["Month"] = dated["Date"].dt.to_period("M").astype(str)
            monthly = dated.groupby("Month")["Amount"].sum()
            st.line_chart(monthly)


# =============== ADD RECEIPT ===============
elif page == "Add receipt":

    st.markdown("""
    <div class="hero">
        <div class="hero-kicker">Capture · Review · Save</div>
        <div class="hero-title">Add an expense</div>
        <p class="hero-copy">
            Upload a receipt, extract details with AI if configured,
            and review everything before saving.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload a receipt image",
        type=["png", "jpg", "jpeg", "webp"],
        help="Upload a clear receipt photo or screenshot.",
    )

    extracted = st.session_state.extracted.copy()

    if uploaded is not None:
        image_bytes = uploaded.getvalue()

        if (
            st.session_state.receipt_name != uploaded.name
            or st.session_state.receipt_bytes != image_bytes
        ):
            st.session_state.receipt_name = uploaded.name
            st.session_state.receipt_bytes = image_bytes
            st.session_state.extracted = {}
            extracted = {}

        image_col, action_col = st.columns([0.8, 1.2], gap="large")

        with image_col:
            st.image(
                image_bytes,
                caption=uploaded.name,
                width="stretch",
            )

        with action_col:
            st.markdown("### Receipt assistant")
            st.write(
                "Let AI suggest the details, or enter them manually below."
            )

            if st.button(
                "✨ Extract details with Gemma",
                use_container_width=True,
            ):
                with st.spinner("Reading your receipt..."):
                    data, error = extract_receipt(image_bytes)

                if data:
                    st.session_state.extracted = data
                    st.success(
                        "Details extracted. Review them before saving."
                    )
                    st.rerun()
                else:
                    st.warning(error)

    else:
        st.session_state.receipt_name = ""
        st.session_state.receipt_bytes = None
        st.session_state.extracted = {}
        extracted = {}

    st.divider()
    st.subheader("Expense details")

    default_date = extracted.get("date") or str(date.today())

    try:
        default_date = date.fromisoformat(default_date)
    except (ValueError, TypeError):
        default_date = date.today()

    with st.form("expense_form"):

        left, right = st.columns(2)

        with left:
            expense_date = st.date_input(
                "Date",
                value=default_date,
            )

            merchant = st.text_input(
                "Merchant / store",
                value=str(extracted.get("merchant", "")),
                placeholder="e.g. Local supermarket",
            )

            category_default = extracted.get("category", "Other")

            category_index = (
                CATEGORIES.index(category_default)
                if category_default in CATEGORIES
                else CATEGORIES.index("Other")
            )

            category = st.selectbox(
                "Category",
                CATEGORIES,
                index=category_index,
            )

            description = st.text_input(
                "Description",
                value=str(extracted.get("description", "")),
                placeholder="What did you purchase?",
            )

        with right:
            try:
                amount_default = max(
                    float(extracted.get("amount", 0) or 0), 0.0
                )
            except (ValueError, TypeError):
                amount_default = 0.0

            amount = st.number_input(
                "Total amount",
                min_value=0.0,
                value=amount_default,
                step=10.0,
                format="%.2f",
            )

            currency_options = ["INR", "USD", "EUR", "GBP", "Other"]
            currency_default = str(
                extracted.get("currency", "INR")
            ).upper()

            currency_index = (
                currency_options.index(currency_default)
                if currency_default in currency_options
                else 0
            )

            currency = st.selectbox(
                "Currency",
                currency_options,
                index=currency_index,
            )

            payment_options = [
                "Unknown",
                "UPI",
                "Card",
                "Cash",
                "Bank transfer",
                "Other",
            ]

            payment_default = str(
                extracted.get("payment_method", "Unknown")
            ).title()

            payment_index = (
                payment_options.index(payment_default)
                if payment_default in payment_options
                else 0
            )

            payment_method = st.selectbox(
                "Payment method",
                payment_options,
                index=payment_index,
            )

            receipt_filename = st.text_input(
                "Receipt filename",
                value=st.session_state.receipt_name,
            )

        submitted = st.form_submit_button(
            "Save expense",
            use_container_width=True,
        )

        if submitted:
            if not merchant.strip():
                st.error("Please enter a merchant or store name.")

            elif amount <= 0:
                st.error("Please enter an amount greater than zero.")

            else:
                new_expense = {
                    "Date": expense_date.isoformat(),
                    "Merchant": merchant.strip(),
                    "Category": category,
                    "Description": description.strip(),
                    "Amount": round(float(amount), 2),
                    "Currency": currency,
                    "Payment method": payment_method,
                    "Receipt filename": receipt_filename.strip(),
                }

                st.session_state.expenses = pd.concat(
                    [
                        st.session_state.expenses,
                        pd.DataFrame([new_expense]),
                    ],
                    ignore_index=True,
                )

                st.session_state.extracted = {}
                st.session_state.receipt_bytes = None
                st.session_state.receipt_name = ""

                st.success("Expense saved!")
                st.rerun()
                # =============== EXPENSE HISTORY ===============
elif page == "Expense history":

    st.markdown("""
    <div class="hero">
        <div class="hero-kicker">Your records</div>
        <div class="hero-title">Expense history</div>
        <p class="hero-copy">
            Search your records, filter by category, and export your expenses.
        </p>
    </div>
    """, unsafe_allow_html=True)

    expenses = st.session_state.expenses.copy()

    if expenses.empty:
        st.info("No expenses yet. Add a receipt to start your history.")

    else:
        filter_col, search_col = st.columns([1, 1.4])

        with filter_col:
            category_filter = st.selectbox(
                "Filter category",
                ["All categories"] + CATEGORIES,
            )

        with search_col:
            search_term = st.text_input(
                "Search expenses",
                placeholder="Search merchant or description",
            )

        view = expenses.copy()

        if category_filter != "All categories":
            view = view[view["Category"] == category_filter]

        if search_term.strip():
            term = search_term.strip().lower()

            matches = (
                view["Merchant"].astype(str).str.lower().str.contains(
                    term, na=False
                )
                | view["Description"].astype(str).str.lower().str.contains(
                    term, na=False
                )
            )

            view = view[matches]

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = expenses.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "⬇ Download all expenses as CSV",
            data=csv_data,
            file_name="receiptsort_expenses.csv",
            mime="text/csv",
            use_container_width=True,
        )

        with st.expander("Delete an expense"):
            options = [
                f"{idx} | {row['Date']} | {row['Merchant']} | "
                f"{row['Amount']} {row['Currency']}"
                for idx, row in expenses.iterrows()
            ]

            selected = st.selectbox("Select an expense", options)

            if st.button("Delete selected expense"):
                row_index = int(selected.split(" | ", 1)[0])

                st.session_state.expenses = (
                    expenses.drop(index=row_index)
                    .reset_index(drop=True)
                )

                st.success("Expense deleted.")
                st.rerun()

        st.caption(
            "Expenses are stored in the current Streamlit session. "
            "Download the CSV to keep a permanent copy."
        )


# =============== SETTINGS ===============
elif page == "Settings":

    st.markdown("""
    <div class="hero">
        <div class="hero-kicker">Your workspace</div>
        <div class="hero-title">Settings</div>
        <p class="hero-copy">
            Configure optional AI extraction and manage your current session.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Gemma AI configuration")

    st.write(
        "ReceiptSort AI supports manual expense tracking without an API key. "
        "Configure a compatible model key to enable AI receipt extraction."
    )

    api_key = st.text_input(
        "Google AI API key",
        type="password",
        value=st.session_state.api_key,
        help="Stored in Streamlit session state for this session.",
    )

    if st.button("Save API key"):
        st.session_state.api_key = api_key.strip()
        st.success("API key saved for this session.")

    model_name = os.getenv("GEMMA_MODEL", "gemini-3.5-flash-lite")

    st.caption(f"Configured model: {model_name}")

    if genai is None:
        st.info(
            "AI package is missing. Install it with: "
            "pip install google-genai"
        )

    st.divider()
    st.subheader("Data and privacy")

    st.markdown("""
    - Expenses are stored in Streamlit session state.
    - Export your CSV to keep your records outside the session.
    - Receipt images are not embedded in the CSV.
    - If AI extraction is enabled, the uploaded image is sent to the
      configured model provider for processing.
    """)

    st.divider()
    st.subheader("Clear session data")

    if st.button("Clear all expenses"):
        st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear", False):
        st.warning("This will delete all expenses in the current session.")

        yes_col, no_col = st.columns(2)

        with yes_col:
            if st.button("Yes, clear all"):
                st.session_state.expenses = empty_expenses()
                st.session_state.confirm_clear = False
                st.success("Expenses cleared.")
                st.rerun()

        with no_col:
            if st.button("Cancel"):
                st.session_state.confirm_clear = False
                st.rerun()


# =============== FOOTER ===============
st.markdown("""
<div style="
    text-align:center;
    color:#718075;
    font-size:12px;
    padding:35px 0 10px 0;
">
    ReceiptSort AI · Expense tracking, thoughtfully organized
</div>
""", unsafe_allow_html=True)