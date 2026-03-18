import streamlit as st
import pandas as pd
import requests
import smtplib
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Gmail SMTP credentials (Use environment variables for security)
SENDER_EMAIL = "sanjaybukka11@gmail.com"
SENDER_PASSWORD = "ibvo mevq mgjv lbah"  # Consider using Streamlit secrets for security

# Gemini API Key (Use environment variables for security)
GEMINI_API_KEY = "AIzaSyAFwlMAy6mHBQyGoLaQb6BDF8rUBGtDyiA"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def extract_name(email):
    """Extracts name from email address."""
    return email.split('@')[0].replace('.', ' ').title()

def generate_email_with_gemini(subject, name, company_name, hiring_manager, filename, score, skills, qualified):
    """
    Generates a professional job application response email using Gemini AI.
    """
    prompt = f"""
    Write a professional email for a job application response with the following details:
    - Subject: {subject}
    - Candidate Name: {name}
    - Company Name: {company_name}
    - Hiring Manager: {hiring_manager}
    - Candidate's Resume: {filename}
    - Overall Score: {score}
    - Key Skills: {skills}
    - Qualification Status: {'Qualified' if qualified else 'Not Qualified'}
    
    The email should:
    1. Thank the candidate for their application.
    2. Mention their overall score and notable skills.
    3. {'Include next steps or feedback based on their score.' if qualified else 'Politely inform them that they did not qualify and encourage future applications.'}
    4. Maintain a professional and encouraging tone.
    """
    try:
        response = model.generate_content(prompt)
        return response.text if response else "Error: No response from AI."
    except Exception as e:
        st.error(f"Error generating email content: {e}")
        return None

def send_email(recipient_email, subject, message_body):
    """
    Sends an email via Gmail SMTP.
    """
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message_body, "plain"))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Error sending email to {recipient_email}: {e}")
        return False

# Streamlit UI
st.title("Resume Ranking Email Sender")
st.write("Upload a CSV file with resume ranking data and send automated emails.")

# Company and Hiring Manager Details
company_name = st.text_input("Enter Company Name")
hiring_manager = st.text_input("Enter Hiring Manager Name")

# Threshold selection
threshold = st.slider("Set Qualification Threshold (0 to 1)", 0.0, 1.0, 0.5)

# File upload
uploaded_file = st.file_uploader("Upload CSV file with resume ranking data", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Preview of Uploaded Data:", df.head())
    
    if "email" not in df.columns or "score" not in df.columns or "skills" not in df.columns:
        st.error("CSV must contain 'Email', 'Score', and 'Skills' columns.")
    else:
        if st.button("Send Emails"):
            for index, row in df.iterrows():
                email = row["email"]
                name = extract_name(email)
                score = row["score"]
                skills = row["skills"]
                filename = row.get("Resume Filename", "N/A")
                subject = "Job Application Status"
                
                qualified = score >= threshold
                email_body = generate_email_with_gemini(subject, name, company_name, hiring_manager, filename, score, skills, qualified)
                
                if email_body and send_email(email, subject, email_body):
                    st.success(f"Email sent successfully to {email}")
                else:
                    st.error(f"Failed to send email to {email}")
