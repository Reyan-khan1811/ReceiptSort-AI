# 🧾 ReceiptSort AI

**An AI-powered expense tracking and receipt management app built with Python and Streamlit.**

ReceiptSort AI helps users record expenses, organize spending, analyze expense patterns, and export expense records in CSV format.

## ✨ Features

- 📊 Expense dashboard with spending summaries and charts
- ✍️ Manual expense entry
- 🧾 Receipt image upload
- 🤖 Optional AI-powered receipt data extraction using Google's Gemini API
- 🔎 Expense history and filtering
- 📁 Export expense records to CSV
- 🌿 Clean, minimal dashboard interface

## 🛠️ Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Pillow
- Google Gemini API

## 🚀 Run Locally

1. Clone this repository:

   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL
   ```

2. Open the project folder:

   ```bash
   cd ReceiptSort-AI
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   streamlit run app.py
   ```

## 🔐 API Key Security

AI-powered receipt extraction may require a Google Gemini API key. Keep API keys private and never commit them to GitHub. Configure secrets securely when deploying.

## 🎯 Project Goal

The goal of ReceiptSort AI is to make everyday expense tracking simpler by combining expense management, data visualization, and optional AI-assisted receipt processing.

## 📌 Project Status

Developed as a learning project exploring Python, AI integration, data visualization, and application deployment.

Live demo: https://receiptsort-ai.streamlit.app/

---

**Built with Python and Streamlit.**
