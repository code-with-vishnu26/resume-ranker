# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from resume_parser import (
    extract_text_from_resume, extract_email, extract_phone, extract_skills,
    extract_soft_skills, detect_bias_indicators, extract_resumes_from_zip,
    parse_linkedin_text, detect_language, translate_text, anonymize_resume
)
from resume_ranker import rank_resumes
from database import (
    init_db, create_user, verify_user, save_session, get_user_sessions,
    load_session, get_all_sessions_for_trends, delete_session,
    save_custom_skills, get_custom_skills
)
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os, time, io, json, zipfile, tempfile

# ─── Page Config ───
st.set_page_config(page_title="Resume Ranker Pro", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

# ─── Theme State ───
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

dm = st.session_state.dark_mode
BG1 = "#0f0c29" if dm else "#f7f8fc"
BG2 = "#1a1a2e" if dm else "#ffffff"
BG3 = "#16213e" if dm else "#eef1f6"
TXT = "#e2e8f0" if dm else "#1a202c"
TXT2 = "#a0aec0" if dm else "#4a5568"
CARD_BG = "rgba(255,255,255,0.03)" if dm else "rgba(0,0,0,0.02)"
CARD_BD = "rgba(255,255,255,0.08)" if dm else "rgba(0,0,0,0.08)"
ACCENT = "#667eea"
ACCENT2 = "#764ba2"

# ─── CSS ───
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* {{ font-family: 'Inter', sans-serif; }}
.main {{ background: linear-gradient(135deg, {BG1}, {BG2}, {BG3}); }}
.stApp {{ background: linear-gradient(135deg, {BG1} 0%, {BG2} 50%, {BG3} 100%); }}
.main-title {{ text-align:center; font-size:2.8rem; font-weight:800;
    background: linear-gradient(135deg, #667eea, #764ba2, #f093fb);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0; padding-top:1rem; }}
.subtitle {{ text-align:center; color:{TXT2}; font-size:1.1rem; font-weight:300; margin-bottom:2rem; }}
.metric-card {{ background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.1));
    border:1px solid rgba(102,126,234,0.3); border-radius:16px; padding:1.5rem;
    text-align:center; backdrop-filter:blur(10px); transition:transform 0.3s ease, box-shadow 0.3s ease; }}
.metric-card:hover {{ transform:translateY(-4px); box-shadow:0 8px 30px rgba(102,126,234,0.3); }}
.metric-value {{ font-size:2rem; font-weight:700; background:linear-gradient(135deg,#667eea,#764ba2);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.metric-label {{ font-size:0.85rem; color:{TXT2}; margin-top:0.3rem; text-transform:uppercase; letter-spacing:1px; }}
.candidate-card {{ background:{CARD_BG}; border:1px solid {CARD_BD}; border-radius:16px;
    padding:1.5rem; margin-bottom:1rem; backdrop-filter:blur(10px); transition:all 0.3s ease; }}
.candidate-card:hover {{ border-color:rgba(102,126,234,0.4); box-shadow:0 4px 20px rgba(102,126,234,0.15); }}
.rank-badge {{ display:inline-block; background:linear-gradient(135deg,#667eea,#764ba2);
    color:white; padding:0.3rem 0.8rem; border-radius:20px; font-weight:700; font-size:0.85rem; }}
.skill-tag {{ display:inline-block; background:rgba(102,126,234,0.15); color:#667eea;
    padding:0.25rem 0.7rem; border-radius:20px; font-size:0.78rem; margin:0.15rem;
    border:1px solid rgba(102,126,234,0.3); }}
.keyword-matched {{ display:inline-block; background:rgba(72,187,120,0.15); color:#48bb78;
    padding:0.2rem 0.6rem; border-radius:12px; font-size:0.75rem; margin:0.1rem;
    border:1px solid rgba(72,187,120,0.3); }}
.keyword-missing {{ display:inline-block; background:rgba(245,101,101,0.15); color:#f56565;
    padding:0.2rem 0.6rem; border-radius:12px; font-size:0.75rem; margin:0.1rem;
    border:1px solid rgba(245,101,101,0.3); }}
.section-header {{ font-size:1.3rem; font-weight:600; color:{TXT}; margin:1.5rem 0 1rem 0;
    padding-bottom:0.5rem; border-bottom:2px solid rgba(102,126,234,0.3); }}
.stTabs [data-baseweb="tab-list"] {{ gap:8px; background:rgba(255,255,255,0.03); border-radius:12px; padding:0.5rem; }}
.stTabs [data-baseweb="tab"] {{ border-radius:8px; color:{TXT2}; font-weight:500; padding:0.5rem 1.5rem; }}
.stTabs [aria-selected="true"] {{ background:linear-gradient(135deg,rgba(102,126,234,0.2),rgba(118,75,162,0.2)); color:#667eea; }}
div[data-testid="stExpander"] {{ background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:12px; }}
.stButton > button {{ background:linear-gradient(135deg,#667eea,#764ba2); color:white; border:none;
    border-radius:10px; padding:0.6rem 2rem; font-weight:600; transition:all 0.3s ease; }}
.stButton > button:hover {{ transform:translateY(-2px); box-shadow:0 4px 15px rgba(102,126,234,0.4); }}
.ai-box {{ background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.08));
    border:1px solid rgba(102,126,234,0.2); border-radius:12px; padding:1rem 1.2rem;
    margin:0.5rem 0; font-size:0.92rem; line-height:1.6; color:#cbd5e0; }}
.bias-badge {{ display:inline-block; background:rgba(237,137,54,0.15); color:#ed8936;
    padding:0.2rem 0.6rem; border-radius:8px; font-size:0.72rem; margin:0.1rem;
    border:1px solid rgba(237,137,54,0.3); }}
.chat-msg-user {{ background:rgba(102,126,234,0.15); border-radius:12px 12px 2px 12px; padding:0.8rem 1rem;
    margin:0.5rem 0; color:{TXT}; text-align:right; }}
.chat-msg-ai {{ background:rgba(118,75,162,0.1); border-radius:12px 12px 12px 2px; padding:0.8rem 1rem;
    margin:0.5rem 0; color:{TXT}; }}
@media (max-width: 768px) {{
    .main-title {{ font-size:1.8rem; }}
    .metric-card {{ padding:0.8rem; }}
    .metric-value {{ font-size:1.4rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ─── Gemini AI Setup ───
GEMINI_API_KEY = "AIzaSyAFwlMAy6mHBQyGoLaQb6BDF8rUBGtDyiA"
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-pro')
SENDER_EMAIL = "sanjaybukka11@gmail.com"
SENDER_PASSWORD = "ibvo mevq mgjv lbah"

# ─── Job Role Templates ───
JOB_TEMPLATES = {
    "Custom": "",
    "Software Engineer": """Software Engineer - Requirements:
- 3+ years of experience in software development
- Proficiency in Python, Java, or C++. Knowledge of data structures and algorithms.
- Experience with REST APIs, microservices architecture, Docker, Kubernetes.
- Bachelor's degree in Computer Science. Git, CI/CD, Agile/Scrum.
- Strong problem solving, communication, and teamwork skills.""",
    "Data Scientist": """Data Scientist - Requirements:
- 2+ years experience in data science or analytics. Master's degree preferred.
- Python, R, SQL, machine learning, deep learning, TensorFlow, PyTorch, scikit-learn.
- Data visualization: Tableau, Power BI, matplotlib. Statistical analysis.
- NLP, computer vision, big data tools. Communication, presentation skills.""",
    "Product Manager": """Product Manager - Requirements:
- 3+ years product management experience. Bachelor's degree required, MBA preferred.
- Agile, Scrum, Jira, roadmap planning, project management.
- Data analysis, A/B testing, user research. Strong leadership and communication.
- Cross-functional collaboration, strategic thinking, customer service.""",
    "DevOps Engineer": """DevOps Engineer - Requirements:
- 3+ years DevOps/SRE experience. AWS, Azure, or GCP certification preferred.
- Docker, Kubernetes, Terraform, Jenkins, CI/CD pipelines.
- Linux, Python/Bash scripting, monitoring tools. Git, GitLab.
- Infrastructure as code, microservices. Problem solving, teamwork.""",
    "Frontend Developer": """Frontend Developer - Requirements:
- 2+ years frontend development. Proficiency in HTML, CSS, JavaScript, TypeScript.
- React, Angular, or Vue.js. Responsive design, web accessibility.
- REST APIs, GraphQL, Git, testing frameworks. UI/UX sensibility.
- Communication, attention to detail, creativity.""",
    "Backend Developer": """Backend Developer - Requirements:
- 3+ years backend development. Python, Java, Node.js, or Go.
- Django, Flask, Spring Boot, Express.js. PostgreSQL, MongoDB, Redis.
- REST APIs, GraphQL, microservices, Docker. Authentication, security.
- Problem solving, system design, teamwork.""",
    "ML Engineer": """Machine Learning Engineer - Requirements:
- 2+ years ML engineering. Master's or PhD preferred.
- Python, TensorFlow, PyTorch, scikit-learn, Keras.
- Deep learning, NLP, computer vision, transfer learning, LLM, OpenAI, LangChain.
- MLOps, Docker, cloud computing (AWS/GCP). Data engineering, pandas, numpy.
- Research skills, analytical thinking, communication.""",
    "Full Stack Developer": """Full Stack Developer - Requirements:
- 3+ years full stack development. Bachelor's degree in CS.
- Frontend: React, Angular, HTML, CSS, JavaScript, TypeScript.
- Backend: Node.js, Python, Django, Flask, Express.js.
- Database: PostgreSQL, MongoDB, MySQL. Docker, Git, CI/CD.
- REST APIs, cloud computing, agile, problem solving, teamwork.""",
}

# ─── Session State ───
defaults = {
    'ranked_results': None, 'job_description': "", 'ai_summaries': {},
    'ai_feedback': {}, 'chat_history': [], 'authenticated': False,
    'user': None, 'ab_results_b': None, 'ab_jd_b': "",
    'custom_weights': {'content': 0.25, 'skill': 0.25, 'formatting': 0.10,
                       'experience': 0.15, 'education': 0.10, 'culture_fit': 0.15},
    'candidate_notes': {}, 'candidate_tags': {}, 'shortlisted': {},
    'ai_explanations': {}, 'anonymize_mode': False,
    'email_templates': {
        'Qualified': """Dear {name},\n\nThank you for applying to {company}. We are pleased to inform you that your profile matches our requirements with a score of {score}.\n\nWe would like to invite you for the next round of interviews. Our team will reach out shortly with scheduling details.\n\nBest regards,\n{manager}""",
        'Not Qualified': """Dear {name},\n\nThank you for your interest in {company}. After careful review, we have decided to proceed with other candidates at this time.\n\nWe encourage you to apply for future openings.\n\nBest regards,\n{manager}""",
        'On Hold': """Dear {name},\n\nThank you for applying to {company}. Your application is currently under review. We will update you on the status within the next few days.\n\nBest regards,\n{manager}""",
    },
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── AI Functions ───
def generate_ai_summary(resume_text, filename):
    prompt = f"""Analyze this resume and provide a brief professional summary in 3-4 sentences.
Focus on: key strengths, experience level, primary domain, and standout qualifications.
Resume ({filename}): {resume_text[:3000]}"""
    try:
        return ai_model.generate_content(prompt).text or "Summary unavailable."
    except Exception as e:
        return f"Could not generate summary: {str(e)}"

def generate_ai_feedback(resume_text, job_description, score, skills, missing_keywords):
    prompt = f"""As an expert career coach, provide 4-5 specific, actionable improvement suggestions for this resume.
Job Description: {job_description[:1500]}
Candidate's Match Score: {score:.0%}
Skills Found: {', '.join(skills[:15])}
Missing Keywords: {', '.join(missing_keywords[:15])}
Resume Excerpt: {resume_text[:2500]}
Format as numbered bullet points. Keep each suggestion to 1-2 sentences."""
    try:
        return ai_model.generate_content(prompt).text or "Feedback unavailable."
    except Exception as e:
        return f"Could not generate feedback: {str(e)}"

def generate_email_with_gemini(subject, name, company_name, hiring_manager, filename, score, skills, qualified):
    prompt = f"""Write a professional email for a job application response:
Subject: {subject}, Candidate: {name}, Company: {company_name}, Manager: {hiring_manager},
Score: {score:.0%}, Skills: {', '.join(skills[:10]) if isinstance(skills, list) else skills},
Status: {'Qualified' if qualified else 'Not Qualified'}.
Thank the candidate, mention score and skills, {'include next steps' if qualified else 'politely inform and encourage future applications'}.
Keep under 200 words."""
    try:
        return ai_model.generate_content(prompt).text
    except:
        return None

def ai_chat_response(question, ranked_results, job_description):
    candidates_info = ""
    for i, c in enumerate(ranked_results[:10], 1):
        candidates_info += f"#{i} {c['filename']}: Score={c['score']:.0%}, Skills={', '.join(c['skills'][:8])}, Edu={c['education']}, Exp={c['experience_years']}yrs\n"
    prompt = f"""You are an AI recruiting assistant. Answer based on analyzed candidate data.
Job Description: {job_description[:1000]}
Candidates:\n{candidates_info}
Question: {question}
Give a concise, helpful answer."""
    try:
        return ai_model.generate_content(prompt).text or "I couldn't process that question."
    except Exception as e:
        return f"Error: {str(e)}"

def send_email(recipient_email, subject, message_body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message_body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        return True
    except:
        return False

def generate_salary_estimate(skills, experience_years, education, job_description):
    prompt = f"""Estimate a salary range (annual, USD) for a candidate with:
- Skills: {', '.join(skills[:15]) if isinstance(skills, list) else skills}
- Experience: {experience_years} years
- Education: {education}
- Target Role: {job_description[:500]}
Respond with ONLY the format: $XX,000 - $XX,000 (no other text)."""
    try:
        return ai_model.generate_content(prompt).text.strip()
    except:
        return "$50,000 - $80,000"

def generate_ai_explanation(candidate, job_description):
    prompt = f"""Explain in 3-4 bullet points WHY this candidate scored {candidate['score']:.0%} for this role.
Candidate: Skills={', '.join(candidate['skills'][:10])}, Exp={candidate['experience_years']}yrs, Edu={candidate['education']},
Content Match={candidate['content_score']:.0%}, Skill Match={candidate['skill_score']:.0%}, Culture Fit={candidate.get('culture_fit_score',0):.0%}
Matched Keywords: {', '.join(candidate['matched_keywords'][:10])}
Missing Keywords: {', '.join(candidate['missing_keywords'][:10])}
Job Description: {job_description[:800]}
Be specific and actionable. Use bullet points."""
    try:
        return ai_model.generate_content(prompt).text or "Explanation unavailable."
    except Exception as e:
        return f"Could not generate explanation: {str(e)}"

def generate_pdf_report(ranked, job_description):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title Page
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 28)
    pdf.cell(0, 60, '', ln=True)
    pdf.cell(0, 15, 'Resume Ranker Pro', ln=True, align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.cell(0, 10, 'AI-Powered Resume Screening Report', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 10, f'Generated: {time.strftime("%B %d, %Y %I:%M %p")}', ln=True, align='C')
    pdf.cell(0, 8, f'Total Candidates: {len(ranked)}', ln=True, align='C')
    avg = np.mean([c["score"] for c in ranked])
    pdf.cell(0, 8, f'Average Score: {avg:.0%}', ln=True, align='C')

    # Rankings Summary
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 12, 'Candidate Rankings', ln=True)
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(102, 126, 234)
    pdf.set_text_color(255, 255, 255)
    col_w = [12, 55, 55, 20, 20, 20]
    headers = ['Rank', 'Candidate', 'Email', 'Score', 'Exp(yr)', 'Education']
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(0, 0, 0)
    for rank, c in enumerate(ranked, 1):
        pdf.cell(col_w[0], 7, str(rank), border=1, align='C')
        pdf.cell(col_w[1], 7, c['filename'][:28], border=1)
        pdf.cell(col_w[2], 7, c['email'][:28], border=1)
        pdf.cell(col_w[3], 7, f"{c['score']:.0%}", border=1, align='C')
        pdf.cell(col_w[4], 7, str(c['experience_years']), border=1, align='C')
        pdf.cell(col_w[5], 7, c['education'][:12], border=1, align='C')
        pdf.ln()

    # Individual candidate pages
    for rank, c in enumerate(ranked[:10], 1):
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f'#{rank}  {c["filename"]}', ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, f'Overall Score: {c["score"]:.0%}  |  Email: {c["email"]}  |  Exp: {c["experience_years"]} yrs  |  Edu: {c["education"]}', ln=True)
        pdf.ln(3)

        # Score breakdown
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, 'Score Breakdown', ln=True)
        pdf.set_font('Helvetica', '', 9)
        scores = [
            ('Content Match', c['content_score']), ('Skill Match', c['skill_score']),
            ('Formatting', c['formatting_score']), ('Experience', c['experience_score']),
            ('Education', c['education_score']), ('Culture Fit', c.get('culture_fit_score', 0)),
        ]
        for name, val in scores:
            bar_w = int(val * 100)
            pdf.cell(35, 6, f'{name}:', align='R')
            pdf.set_fill_color(102, 126, 234)
            pdf.cell(bar_w, 6, '', fill=True)
            pdf.cell(20, 6, f' {val:.0%}')
            pdf.ln()
        pdf.ln(3)

        # Skills
        if c['skills']:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 8, 'Skills', ln=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, ', '.join(c['skills']))
            pdf.ln(2)

        # Keywords
        if c['matched_keywords']:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 8, 'Matched Keywords', ln=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, ', '.join(c['matched_keywords'][:20]))
        if c['missing_keywords']:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 8, 'Missing Keywords', ln=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, ', '.join(c['missing_keywords'][:20]))

    output = io.BytesIO()
    pdf_bytes = pdf.output()
    output.write(pdf_bytes)
    output.seek(0)
    return output

# ─── Helpers ───
def get_score_color(score):
    if score >= 0.7: return "#48bb78"
    elif score >= 0.4: return "#ecc94b"
    else: return "#f56565"

def create_ats_breakdown_chart(candidate):
    categories = ['Content', 'Skills', 'Format', 'Experience', 'Education', 'Culture Fit']
    scores = [candidate['content_score'], candidate['skill_score'], candidate['formatting_score'],
              candidate['experience_score'], candidate['education_score'], candidate.get('culture_fit_score', 0)]
    fig = go.Figure()
    colors = ['#667eea', '#764ba2', '#f093fb', '#48bb78', '#ecc94b', '#ed8936']
    fig.add_trace(go.Bar(x=scores, y=categories, orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        text=[f'{s:.0%}' for s in scores], textposition='auto',
        textfont=dict(color='white', size=12, family='Inter')))
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a0aec0', family='Inter'),
        xaxis=dict(range=[0,1], showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='.0%'),
        yaxis=dict(showgrid=False), margin=dict(l=10,r=10,t=10,b=10), height=220, bargap=0.3)
    return fig

def generate_excel_report(ranked, job_description):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#667eea', 'font_color': 'white',
            'border': 1, 'text_wrap': True, 'valign': 'vcenter', 'font_name': 'Calibri', 'font_size': 11})
        cell_fmt = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'vcenter',
            'font_name': 'Calibri', 'font_size': 10})
        pct_fmt = workbook.add_format({'border': 1, 'num_format': '0.0%', 'valign': 'vcenter',
            'font_name': 'Calibri', 'font_size': 10})

        # Sheet 1: Rankings
        rankings = []
        for i, r in enumerate(ranked, 1):
            rankings.append({'Rank': i, 'Candidate': r['filename'], 'Email': r['email'],
                'Phone': r['phone'], 'Overall Score': r['score'], 'Content': r['content_score'],
                'Skills': r['skill_score'], 'Formatting': r['formatting_score'],
                'Experience': r['experience_score'], 'Education Score': r['education_score'],
                'Culture Fit': r.get('culture_fit_score', 0), 'Education': r['education'],
                'Exp (Years)': r['experience_years']})
        df1 = pd.DataFrame(rankings)
        df1.to_excel(writer, sheet_name='Rankings', index=False, startrow=1)
        ws1 = writer.sheets['Rankings']
        for col_num, val in enumerate(df1.columns):
            ws1.write(0, col_num, val, header_fmt)
            ws1.set_column(col_num, col_num, 15)
        for row in range(len(df1)):
            for col in range(len(df1.columns)):
                v = df1.iloc[row, col]
                if isinstance(v, float) and col >= 4 and col <= 10:
                    ws1.write(row+1, col, v, pct_fmt)

        # Sheet 2: Skills Matrix
        all_skills = sorted(set(s for r in ranked for s in r['skills']))
        skills_data = []
        for r in ranked:
            row = {'Candidate': r['filename']}
            for s in all_skills:
                row[s] = '✓' if s in r['skills'] else ''
            skills_data.append(row)
        df2 = pd.DataFrame(skills_data)
        df2.to_excel(writer, sheet_name='Skills Matrix', index=False, startrow=1)
        ws2 = writer.sheets['Skills Matrix']
        for col_num, val in enumerate(df2.columns):
            ws2.write(0, col_num, val, header_fmt)

        # Sheet 3: Keyword Analysis
        kw_data = []
        for r in ranked:
            kw_data.append({'Candidate': r['filename'],
                'Matched Keywords': ', '.join(r['matched_keywords']),
                'Missing Keywords': ', '.join(r['missing_keywords']),
                'Match Count': len(r['matched_keywords']),
                'Missing Count': len(r['missing_keywords'])})
        df3 = pd.DataFrame(kw_data)
        df3.to_excel(writer, sheet_name='Keywords', index=False, startrow=1)
        ws3 = writer.sheets['Keywords']
        for col_num, val in enumerate(df3.columns):
            ws3.write(0, col_num, val, header_fmt)
            ws3.set_column(col_num, col_num, 30)

        # Sheet 4: AI Summaries
        ai_data = []
        for r in ranked:
            fn = r['filename']
            ai_data.append({'Candidate': fn,
                'AI Summary': st.session_state.ai_summaries.get(fn, 'Not generated'),
                'AI Feedback': st.session_state.ai_feedback.get(fn, 'Not generated')})
        df4 = pd.DataFrame(ai_data)
        df4.to_excel(writer, sheet_name='AI Analysis', index=False, startrow=1)
        ws4 = writer.sheets['AI Analysis']
        for col_num, val in enumerate(df4.columns):
            ws4.write(0, col_num, val, header_fmt)
            ws4.set_column(col_num, col_num, 50)

    output.seek(0)
    return output

# ─── Sidebar: Auth, Settings, History ───
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    # Theme Toggle — use callback to avoid rerun loop
    def _toggle_theme():
        st.session_state.dark_mode = st.session_state._theme_toggle_val
    st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode,
              key="_theme_toggle_val", on_change=_toggle_theme)

    st.markdown("---")

    # Authentication
    st.markdown("### 🔐 Account")
    if not st.session_state.authenticated:
        auth_tab = st.radio("", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
        if auth_tab == "Login":
            login_user = st.text_input("Username", key="login_u")
            login_pass = st.text_input("Password", type="password", key="login_p")
            if st.button("Login", key="login_btn"):
                ok, user = verify_user(login_user, login_pass)
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.success(f"Welcome, {user['full_name'] or user['username']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        else:
            su_user = st.text_input("Username", key="su_u")
            su_pass = st.text_input("Password", type="password", key="su_p")
            su_name = st.text_input("Full Name", key="su_n")
            su_comp = st.text_input("Company", key="su_c")
            if st.button("Create Account", key="su_btn"):
                ok, msg = create_user(su_user, su_pass, su_name, su_comp)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        user = st.session_state.user
        st.markdown(f"👤 **{user['full_name'] or user['username']}**")
        if user.get('company'):
            st.markdown(f"🏢 {user['company']}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

        # Session History
        st.markdown("---")
        st.markdown("### 📂 History")
        sessions = get_user_sessions(user['id'])
        if sessions:
            for s in sessions[:10]:
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    if st.button(f"📋 {s['session_name'][:20]}", key=f"hist_{s['id']}"):
                        loaded = load_session(s['id'])
                        if loaded:
                            st.session_state.ranked_results = loaded['results']
                            st.session_state.job_description = loaded['job_description']
                            st.rerun()
                with col_h2:
                    if st.button("🗑️", key=f"del_{s['id']}"):
                        delete_session(s['id'])
                        st.rerun()
        else:
            st.caption("No saved sessions yet.")

    # Custom Weights
    st.markdown("---")
    st.markdown("### ⚖️ Score Weights")
    w = st.session_state.custom_weights
    w['content'] = st.slider("Content Match", 0.0, 1.0, w['content'], 0.05, key="w_c")
    w['skill'] = st.slider("Skill Match", 0.0, 1.0, w['skill'], 0.05, key="w_s")
    w['formatting'] = st.slider("Formatting", 0.0, 1.0, w['formatting'], 0.05, key="w_f")
    w['experience'] = st.slider("Experience", 0.0, 1.0, w['experience'], 0.05, key="w_e")
    w['education'] = st.slider("Education", 0.0, 1.0, w['education'], 0.05, key="w_ed")
    w['culture_fit'] = st.slider("Culture Fit", 0.0, 1.0, w['culture_fit'], 0.05, key="w_cf")
    total_w = sum(w.values())
    if total_w > 0:
        st.caption(f"Total: {total_w:.2f} (will be normalized)")

    # Custom Skills
    st.markdown("---")
    st.markdown("### 🏷️ Custom Skills")
    new_skill = st.text_input("Add skill", placeholder="e.g., Figma", key="add_skill")
    if st.button("➕ Add", key="add_skill_btn") and new_skill:
        if 'custom_skill_list' not in st.session_state:
            st.session_state.custom_skill_list = []
        st.session_state.custom_skill_list.append({'name': new_skill, 'category': 'custom'})
        st.rerun()
    if 'custom_skill_list' in st.session_state and st.session_state.custom_skill_list:
        for i, s in enumerate(st.session_state.custom_skill_list):
            st.caption(f"• {s['name']}")

# ─── Header ───
st.markdown('<h1 class="main-title">🎯 Resume Ranker Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-Powered Resume Screening, Ranking & Recruitment System</p>', unsafe_allow_html=True)

# ─── Tabs ───
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📄 Analysis", "📊 Dashboard", "🔄 Compare", "📧 Email", "🤖 AI Chat", "📈 Trends"])

# ━━━━━━━━━━━━ TAB 1: ANALYSIS ━━━━━━━━━━━━
with tab1:
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown('<div class="section-header">📋 Job Description</div>', unsafe_allow_html=True)
        template = st.selectbox("📌 Use a template", list(JOB_TEMPLATES.keys()), key="jd_template")
        default_jd = JOB_TEMPLATES.get(template, "")
        job_desc = st.text_area("Paste the job description here", value=default_jd, height=180,
            placeholder="Enter the complete job description...", label_visibility="collapsed")

    with col_right:
        st.markdown('<div class="section-header">📁 Upload Resumes</div>', unsafe_allow_html=True)
        upload_mode = st.radio("Upload mode", ["Individual Files", "ZIP Archive", "LinkedIn Profile"],
            horizontal=True, label_visibility="collapsed")

        uploaded_files = []
        linkedin_text = None
        zip_file = None

        if upload_mode == "Individual Files":
            uploaded_files = st.file_uploader("Upload resumes", type=["pdf", "docx", "txt"],
                accept_multiple_files=True, label_visibility="collapsed")
            if uploaded_files:
                st.info(f"📎 {len(uploaded_files)} resume(s) uploaded")

        elif upload_mode == "ZIP Archive":
            zip_file = st.file_uploader("Upload ZIP archive", type=["zip"], label_visibility="collapsed")
            if zip_file:
                st.info(f"📦 ZIP archive uploaded: {zip_file.name}")

        elif upload_mode == "LinkedIn Profile":
            linkedin_text = st.text_area("Paste LinkedIn profile text", height=150,
                placeholder="Copy and paste the LinkedIn profile content here...")
            if linkedin_text:
                st.info("🔗 LinkedIn profile text provided")

    st.markdown("")
    _, analyze_col, _ = st.columns([1, 1, 1])
    with analyze_col:
        analyze_btn = st.button("🚀 Analyze & Rank Resumes", use_container_width=True, type="primary")

    if analyze_btn and job_desc:
        custom_s = st.session_state.get('custom_skill_list', [])
        weights = st.session_state.custom_weights
        # Normalize weights
        total_w = sum(weights.values())
        if total_w > 0:
            norm_weights = {k: v / total_w for k, v in weights.items()}
        else:
            norm_weights = None

        with st.spinner("🔍 Processing resumes with AI..."):
            results = []
            all_files_to_process = []

            # Handle different upload modes
            if upload_mode == "Individual Files" and uploaded_files:
                for file in uploaded_files:
                    temp_path = f"temp_{file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(file.getbuffer())
                    all_files_to_process.append((temp_path, file.name))

            elif upload_mode == "ZIP Archive" and zip_file:
                temp_zip = f"temp_{zip_file.name}"
                with open(temp_zip, "wb") as f:
                    f.write(zip_file.getbuffer())
                extracted = extract_resumes_from_zip(temp_zip)
                for ef in extracted:
                    all_files_to_process.append((ef['path'], ef['name']))
                os.remove(temp_zip)

            elif upload_mode == "LinkedIn Profile" and linkedin_text:
                parsed = parse_linkedin_text(linkedin_text)
                if parsed:
                    results.append({
                        "filename": "LinkedIn_Profile",
                        "text": parsed['text'],
                        "email": parsed['email'],
                        "phone": parsed['phone'],
                    })

            # Process files
            if all_files_to_process:
                progress = st.progress(0)
                for i, (path, name) in enumerate(all_files_to_process):
                    text = extract_text_from_resume(path)
                    # Auto-translate if needed
                    lang = detect_language(text)
                    if lang != "english" and text.strip():
                        with st.spinner(f"🌐 Translating {name}..."):
                            text = translate_text(text)
                    from resume_parser import extract_email as _ee, extract_phone as _ep
                    results.append({
                        "filename": name, "text": text,
                        "email": _ee(text), "phone": _ep(text),
                    })
                    try:
                        os.remove(path)
                    except:
                        pass
                    progress.progress((i + 1) / len(all_files_to_process))
                progress.empty()

            if results:
                ranked = rank_resumes(results, job_desc, custom_s, norm_weights)
                st.session_state.ranked_results = ranked
                st.session_state.job_description = job_desc
                st.session_state.ai_summaries = {}
                st.session_state.ai_feedback = {}

                # Auto-save session if authenticated
                if st.session_state.authenticated:
                    session_name = f"Analysis {time.strftime('%b %d %I:%M%p')}"
                    save_session(st.session_state.user['id'], session_name, job_desc, ranked)

                st.success(f"✅ Successfully analyzed {len(ranked)} resumes!")
            else:
                st.warning("Please upload resumes or provide a LinkedIn profile.")

    # Display results
    if st.session_state.ranked_results:
        ranked = st.session_state.ranked_results

        st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{len(ranked)}</div>
                <div class="metric-label">Total Candidates</div></div>""", unsafe_allow_html=True)
        with m2:
            avg_score = np.mean([c['score'] for c in ranked])
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{avg_score:.0%}</div>
                <div class="metric-label">Avg Match Score</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{ranked[0]['score']:.0%}</div>
                <div class="metric-label">Top Score</div></div>""", unsafe_allow_html=True)
        with m4:
            qualified = sum(1 for c in ranked if c['score'] >= 0.5)
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{qualified}</div>
                <div class="metric-label">Qualified (≥50%)</div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">🏆 Ranked Candidates</div>', unsafe_allow_html=True)
        opt_c1, opt_c2 = st.columns([1, 1])
        with opt_c1:
            st.session_state.anonymize_mode = st.toggle("🔒 Anonymize Mode (Blind Hiring)", value=st.session_state.anonymize_mode, key="anon_toggle")
        with opt_c2:
            shortlisted_count = sum(1 for v in st.session_state.shortlisted.values() if v == 'yes')
            st.markdown(f"**✅ Shortlisted: {shortlisted_count}** · **❌ Rejected: {sum(1 for v in st.session_state.shortlisted.values() if v == 'no')}**")
        for rank, candidate in enumerate(ranked, 1):
            sc = get_score_color(candidate['score'])
            fn = candidate['filename']
            shortlist_status = st.session_state.shortlisted.get(fn, '')
            status_badge = ''
            if shortlist_status == 'yes':
                status_badge = '<span style="background:#48bb78;color:white;padding:0.2rem 0.6rem;border-radius:12px;font-size:0.75rem;margin-left:0.5rem;">✅ Shortlisted</span>'
            elif shortlist_status == 'no':
                status_badge = '<span style="background:#f56565;color:white;padding:0.2rem 0.6rem;border-radius:12px;font-size:0.75rem;margin-left:0.5rem;">❌ Rejected</span>'
            display_name = f"Candidate #{rank}" if st.session_state.anonymize_mode else candidate['filename']
            st.markdown(f"""<div class="candidate-card">
                <span class="rank-badge">#{rank}</span>
                <span style="font-size:1.15rem;font-weight:600;color:{TXT};margin-left:0.8rem;">{display_name}</span>
                {status_badge}
                <span style="float:right;font-size:1.4rem;font-weight:700;color:{sc};">{candidate['score']:.0%}</span>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"📋 Details — {display_name}", expanded=(rank == 1)):
                # ─ Shortlist + Rerank row ─
                act_c1, act_c2, act_c3, act_c4 = st.columns([1, 1, 1, 1])
                with act_c1:
                    if st.button("✅ Shortlist", key=f"sl_y_{rank}"):
                        st.session_state.shortlisted[fn] = 'yes'
                        st.rerun()
                with act_c2:
                    if st.button("❌ Reject", key=f"sl_n_{rank}"):
                        st.session_state.shortlisted[fn] = 'no'
                        st.rerun()
                with act_c3:
                    if rank > 1 and st.button("⬆️ Move Up", key=f"up_{rank}"):
                        r = st.session_state.ranked_results
                        idx = rank - 1
                        r[idx-1], r[idx] = r[idx], r[idx-1]
                        st.rerun()
                with act_c4:
                    if rank < len(ranked) and st.button("⬇️ Move Down", key=f"dn_{rank}"):
                        r = st.session_state.ranked_results
                        idx = rank - 1
                        r[idx], r[idx+1] = r[idx+1], r[idx]
                        st.rerun()

                det1, det2 = st.columns([1, 1])
                with det1:
                    if st.session_state.anonymize_mode:
                        st.markdown("**📧 Email:** [REDACTED]")
                        st.markdown("**📞 Phone:** [REDACTED]")
                    else:
                        st.markdown(f"**📧 Email:** {candidate['email']}")
                        st.markdown(f"**📞 Phone:** {candidate['phone']}")
                    st.markdown(f"**🎓 Education:** {candidate['education']}")
                    st.markdown(f"**💼 Experience:** {candidate['experience_years']} years")
                    if candidate['skills']:
                        skills_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in candidate['skills']])
                        st.markdown(f"**🔧 Skills Found:**<br>{skills_html}", unsafe_allow_html=True)
                    # Soft skills
                    soft = candidate.get('soft_skills', [])
                    if soft:
                        soft_html = " ".join([f'<span class="skill-tag" style="border-color:rgba(237,137,54,0.3);color:#ed8936;background:rgba(237,137,54,0.1);">{s}</span>' for s in soft])
                        st.markdown(f"**🤝 Soft Skills:**<br>{soft_html}", unsafe_allow_html=True)
                    # Bias flags
                    bias = candidate.get('bias_flags', {})
                    if bias:
                        st.markdown("**⚠️ Bias Indicators:**")
                        for cat, kws in bias.items():
                            badges = " ".join([f'<span class="bias-badge">{kw}</span>' for kw in kws])
                            st.markdown(f"*{cat.title()}:* {badges}", unsafe_allow_html=True)

                with det2:
                    st.markdown("**📊 ATS Score Breakdown:**")
                    fig = create_ats_breakdown_chart(candidate)
                    st.plotly_chart(fig, use_container_width=True, key=f"ats_{rank}")

                kw1, kw2 = st.columns(2)
                with kw1:
                    if candidate['matched_keywords']:
                        matched_html = " ".join([f'<span class="keyword-matched">✓ {kw}</span>' for kw in candidate['matched_keywords'][:20]])
                        st.markdown(f"**✅ Matched Keywords:**<br>{matched_html}", unsafe_allow_html=True)
                with kw2:
                    if candidate['missing_keywords']:
                        missing_html = " ".join([f'<span class="keyword-missing">✗ {kw}</span>' for kw in candidate['missing_keywords'][:20]])
                        st.markdown(f"**❌ Missing Keywords:**<br>{missing_html}", unsafe_allow_html=True)

                st.markdown("---")
                ai1, ai2 = st.columns(2)
                with ai1:
                    st.markdown("**🤖 AI Resume Summary**")
                    fn = candidate['filename']
                    if fn not in st.session_state.ai_summaries:
                        if st.button("Generate Summary", key=f"sum_{rank}"):
                            with st.spinner("Generating AI summary..."):
                                resume_text_for_ai = next((r.get('text', '') for r in ranked if r['filename'] == fn), "")
                                summary = generate_ai_summary(resume_text_for_ai or "Resume text not available.", fn)
                                st.session_state.ai_summaries[fn] = summary
                                st.rerun()
                    else:
                        st.markdown(f'<div class="ai-box">{st.session_state.ai_summaries[fn]}</div>', unsafe_allow_html=True)
                with ai2:
                    st.markdown("**💡 AI Improvement Feedback**")
                    fn = candidate['filename']
                    if fn not in st.session_state.ai_feedback:
                        if st.button("Generate Feedback", key=f"fb_{rank}"):
                            with st.spinner("Generating AI feedback..."):
                                resume_text_for_fb = next((r.get('text', '') for r in ranked if r['filename'] == fn), "")
                                feedback = generate_ai_feedback(
                                    resume_text_for_fb or "Resume text not available.",
                                    st.session_state.job_description,
                                    candidate['score'], candidate['skills'], candidate['missing_keywords'])
                                st.session_state.ai_feedback[fn] = feedback
                                st.rerun()
                    else:
                        st.markdown(f'<div class="ai-box">{st.session_state.ai_feedback[fn]}</div>', unsafe_allow_html=True)

                # ─ AI Score Explanation + Salary Estimate ─
                exp_c1, exp_c2 = st.columns(2)
                with exp_c1:
                    st.markdown("**🧠 AI Score Explanation**")
                    if fn not in st.session_state.ai_explanations:
                        if st.button("Explain Score", key=f"explain_{rank}"):
                            with st.spinner("Generating explanation..."):
                                explanation = generate_ai_explanation(candidate, st.session_state.job_description)
                                st.session_state.ai_explanations[fn] = explanation
                                st.rerun()
                    else:
                        st.markdown(f'<div class="ai-box">{st.session_state.ai_explanations[fn]}</div>', unsafe_allow_html=True)
                with exp_c2:
                    st.markdown("**💰 Salary Estimate**")
                    salary_key = f"salary_{fn}"
                    if salary_key not in st.session_state:
                        if st.button("Estimate Salary", key=f"sal_{rank}"):
                            with st.spinner("Estimating salary..."):
                                salary = generate_salary_estimate(
                                    candidate['skills'], candidate['experience_years'],
                                    candidate['education'], st.session_state.job_description)
                                st.session_state[salary_key] = salary
                                st.rerun()
                    else:
                        st.markdown(f'<div class="ai-box" style="font-size:1.1rem;text-align:center;font-weight:600;">{st.session_state[salary_key]}</div>', unsafe_allow_html=True)

                # ─ Tags + Notes ─
                tag_note_c1, tag_note_c2 = st.columns(2)
                with tag_note_c1:
                    tag_options = ["🟢 Strong Fit", "🟡 Moderate Fit", "🔴 Weak Fit", "⭐ Top Pick", "🔄 Follow Up",
                                   "👶 Junior", "👤 Mid-Level", "👑 Senior", "🎯 Exact Match"]
                    current_tags = st.session_state.candidate_tags.get(fn, [])
                    selected_tags = st.multiselect("🏷️ Tags", tag_options, default=current_tags, key=f"tags_{rank}")
                    st.session_state.candidate_tags[fn] = selected_tags
                with tag_note_c2:
                    current_note = st.session_state.candidate_notes.get(fn, "")
                    note = st.text_area("📝 Recruiter Notes", value=current_note, height=80,
                        placeholder="Add notes about this candidate...", key=f"note_{rank}")
                    st.session_state.candidate_notes[fn] = note

        # Export
        st.markdown('<div class="section-header">💾 Export Results</div>', unsafe_allow_html=True)
        exp1, exp2, exp3 = st.columns(3)
        with exp1:
            csv_data = pd.DataFrame([{
                'Rank': i+1, 'Filename': r['filename'], 'Email': r['email'], 'Score': f"{r['score']:.2%}",
                'Skills': ', '.join(r['skills']),
                'Status': st.session_state.shortlisted.get(r['filename'], 'Pending'),
                'Tags': ', '.join(st.session_state.candidate_tags.get(r['filename'], [])),
                'Notes': st.session_state.candidate_notes.get(r['filename'], '')
            } for i, r in enumerate(ranked)])
            st.download_button("📥 Download CSV", csv_data.to_csv(index=False).encode(), "report.csv", "text/csv")
        with exp2:
            excel_data = generate_excel_report(ranked, st.session_state.job_description)
            st.download_button("📊 Download Excel", excel_data, "resume_ranking_report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with exp3:
            pdf_data = generate_pdf_report(ranked, st.session_state.job_description)
            st.download_button("📄 Download PDF Report", pdf_data, "resume_screening_report.pdf",
                "application/pdf")


# ━━━━━━━━━━━━ TAB 2: DASHBOARD ━━━━━━━━━━━━
with tab2:
    if st.session_state.ranked_results:
        ranked = st.session_state.ranked_results
        st.markdown('<div class="section-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("#### 📈 Score Distribution")
            scores = [c['score'] for c in ranked]
            names = [c['filename'].replace('.pdf','').replace('.docx','').replace('.txt','')[:20] for c in ranked]
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Bar(x=names, y=scores,
                marker=dict(color=scores, colorscale=[[0,'#f56565'],[0.5,'#ecc94b'],[1,'#48bb78']], line=dict(width=0)),
                text=[f'{s:.0%}' for s in scores], textposition='outside',
                textfont=dict(color='#a0aec0', family='Inter')))
            fig_dist.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0', family='Inter'), xaxis=dict(showgrid=False, tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='.0%',
                    range=[0, max(scores)*1.2 if scores else 1]),
                margin=dict(l=10,r=10,t=10,b=80), height=350)
            st.plotly_chart(fig_dist, use_container_width=True)

        with d2:
            st.markdown("#### 🔧 Top Skills Across Candidates")
            all_skills = {}
            for c in ranked:
                for skill in c['skills']:
                    all_skills[skill] = all_skills.get(skill, 0) + 1
            if all_skills:
                sorted_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:15]
                fig_skills = go.Figure()
                fig_skills.add_trace(go.Bar(y=[s[0] for s in sorted_skills][::-1], x=[s[1] for s in sorted_skills][::-1],
                    orientation='h', marker=dict(color=[s[1] for s in sorted_skills][::-1],
                        colorscale=[[0,'#764ba2'],[1,'#667eea']], line=dict(width=0)),
                    text=[s[1] for s in sorted_skills][::-1], textposition='auto',
                    textfont=dict(color='white', family='Inter')))
                fig_skills.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a0aec0', family='Inter'),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title='Candidates'),
                    yaxis=dict(showgrid=False), margin=dict(l=10,r=10,t=10,b=10), height=350)
                st.plotly_chart(fig_skills, use_container_width=True)

        d3, d4 = st.columns(2)
        with d3:
            st.markdown("#### 🎯 Average Score Breakdown (with Culture Fit)")
            avgs = [np.mean([c['content_score'] for c in ranked]), np.mean([c['skill_score'] for c in ranked]),
                    np.mean([c['formatting_score'] for c in ranked]), np.mean([c['experience_score'] for c in ranked]),
                    np.mean([c['education_score'] for c in ranked]),
                    np.mean([c.get('culture_fit_score', 0) for c in ranked])]
            cats_r = ['Content', 'Skills', 'Formatting', 'Experience', 'Education', 'Culture Fit']
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=avgs + [avgs[0]], theta=cats_r + [cats_r[0]],
                fill='toself', fillcolor='rgba(102,126,234,0.2)', line=dict(color='#667eea', width=2),
                marker=dict(size=8, color='#667eea'), name='Average'))
            fig_radar.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(range=[0,1], showticklabels=True, gridcolor='rgba(255,255,255,0.1)', tickformat='.0%'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.1)')),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0', family='Inter'), margin=dict(l=40,r=40,t=30,b=30), height=350, showlegend=False)
            st.plotly_chart(fig_radar, use_container_width=True)

        with d4:
            st.markdown("#### 🔴 Skill Gap Analysis")
            jd_skills = extract_skills(st.session_state.job_description)
            if jd_skills:
                skill_coverage = {}
                for skill in jd_skills:
                    count = sum(1 for c in ranked if skill in c['skills'])
                    skill_coverage[skill] = count / len(ranked) if ranked else 0
                sorted_gaps = sorted(skill_coverage.items(), key=lambda x: x[1])
                gap_names = [g[0] for g in sorted_gaps[:15]]
                gap_values = [g[1] for g in sorted_gaps[:15]]
                fig_gap = go.Figure()
                fig_gap.add_trace(go.Bar(y=gap_names, x=gap_values, orientation='h',
                    marker=dict(color=[get_score_color(v) for v in gap_values], line=dict(width=0)),
                    text=[f'{v:.0%}' for v in gap_values], textposition='auto',
                    textfont=dict(color='white', family='Inter')))
                fig_gap.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a0aec0', family='Inter'),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='.0%', range=[0,1]),
                    yaxis=dict(showgrid=False), margin=dict(l=10,r=10,t=10,b=10), height=350)
                st.plotly_chart(fig_gap, use_container_width=True)
            else:
                st.info("No specific skills detected in the job description.")

        # Heatmap
        st.markdown("#### 🗺️ Candidate Comparison Heatmap")
        if len(ranked) >= 2:
            hm_data = [[c['content_score'], c['skill_score'], c['formatting_score'],
                c['experience_score'], c['education_score'], c.get('culture_fit_score', 0), c['score']] for c in ranked]
            hm_names = [c['filename'].replace('.pdf','').replace('.docx','').replace('.txt','')[:22] for c in ranked]
            fig_heat = go.Figure(data=go.Heatmap(z=hm_data,
                x=['Content','Skills','Format','Experience','Education','Culture Fit','Overall'], y=hm_names,
                colorscale=[[0,'#1a1a2e'],[0.3,'#764ba2'],[0.6,'#667eea'],[1,'#48bb78']],
                text=[[f'{v:.0%}' for v in row] for row in hm_data], texttemplate='%{text}',
                textfont=dict(size=11, color='white', family='Inter'),
                hovertemplate='%{y}<br>%{x}: %{z:.1%}<extra></extra>'))
            fig_heat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0', family='Inter'), margin=dict(l=10,r=10,t=10,b=10),
                height=max(200, len(ranked)*50), yaxis=dict(autorange='reversed'))
            st.plotly_chart(fig_heat, use_container_width=True)

        # Diversity Dashboard
        st.markdown('<div class="section-header">🌍 Diversity Analytics</div>', unsafe_allow_html=True)
        div1, div2, div3 = st.columns(3)
        with div1:
            st.markdown("#### 🎓 Education Distribution")
            edu_counts = {}
            for c in ranked:
                edu = c.get('education', 'Not specified')
                edu_counts[edu] = edu_counts.get(edu, 0) + 1
            fig_edu = go.Figure(data=[go.Pie(labels=list(edu_counts.keys()), values=list(edu_counts.values()),
                hole=0.4, marker=dict(colors=['#667eea','#764ba2','#f093fb','#48bb78','#ecc94b','#ed8936']),
                textinfo='percent+label', textfont=dict(size=10, color='white'))])
            fig_edu.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0'), margin=dict(l=10,r=10,t=10,b=10), height=250, showlegend=False)
            st.plotly_chart(fig_edu, use_container_width=True)

        with div2:
            st.markdown("#### 💼 Experience Distribution")
            exp_ranges = {'0-2 yrs': 0, '3-5 yrs': 0, '6-10 yrs': 0, '10+ yrs': 0}
            for c in ranked:
                yrs = c.get('experience_years', 0)
                if yrs <= 2: exp_ranges['0-2 yrs'] += 1
                elif yrs <= 5: exp_ranges['3-5 yrs'] += 1
                elif yrs <= 10: exp_ranges['6-10 yrs'] += 1
                else: exp_ranges['10+ yrs'] += 1
            fig_exp = go.Figure(data=[go.Pie(labels=list(exp_ranges.keys()), values=list(exp_ranges.values()),
                hole=0.4, marker=dict(colors=['#48bb78','#667eea','#764ba2','#f093fb']),
                textinfo='percent+label', textfont=dict(size=10, color='white'))])
            fig_exp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0'), margin=dict(l=10,r=10,t=10,b=10), height=250, showlegend=False)
            st.plotly_chart(fig_exp, use_container_width=True)

        with div3:
            st.markdown("#### 🏷️ Score Tier Distribution")
            tiers = {'🟢 High (70%+)': 0, '🟡 Medium (40-70%)': 0, '🔴 Low (<40%)': 0}
            for c in ranked:
                if c['score'] >= 0.7: tiers['🟢 High (70%+)'] += 1
                elif c['score'] >= 0.4: tiers['🟡 Medium (40-70%)'] += 1
                else: tiers['🔴 Low (<40%)'] += 1
            fig_tier = go.Figure(data=[go.Pie(labels=list(tiers.keys()), values=list(tiers.values()),
                hole=0.4, marker=dict(colors=['#48bb78','#ecc94b','#f56565']),
                textinfo='percent+label', textfont=dict(size=10, color='white'))])
            fig_tier.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a0aec0'), margin=dict(l=10,r=10,t=10,b=10), height=250, showlegend=False)
            st.plotly_chart(fig_tier, use_container_width=True)
    else:
        st.markdown("""<div style="text-align:center;padding:4rem 2rem;color:#a0aec0;">
            <h3>📊 No data to display yet</h3>
            <p>Go to the <b>Analysis</b> tab, upload resumes and analyze them to see the dashboard.</p>
        </div>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━ TAB 3: COMPARE ━━━━━━━━━━━━
with tab3:
    if st.session_state.ranked_results:
        ranked = st.session_state.ranked_results
        st.markdown('<div class="section-header">🔄 Side-by-Side Comparison</div>', unsafe_allow_html=True)

        # A/B Testing Mode
        ab_mode = st.toggle("🧪 A/B JD Testing Mode", key="ab_toggle")

        if ab_mode:
            st.markdown("#### Compare rankings across two job descriptions")
            ab1, ab2 = st.columns(2)
            with ab1:
                st.markdown("**JD A** (current)")
                st.text_area("Job Description A", value=st.session_state.job_description, height=120, disabled=True, key="jd_a_display")
            with ab2:
                jd_b = st.text_area("Job Description B", height=120, placeholder="Paste alternate JD here...", key="jd_b_input")

            if st.button("🔄 Run A/B Comparison", type="primary") and jd_b:
                with st.spinner("Running A/B analysis..."):
                    resumes_data = [{'filename': r['filename'], 'text': r.get('text', ''), 'email': r['email'], 'phone': r['phone']}
                        for r in ranked]
                    ranked_b = rank_resumes(resumes_data, jd_b, st.session_state.get('custom_skill_list', []))
                    st.session_state.ab_results_b = ranked_b
                    st.session_state.ab_jd_b = jd_b

            if st.session_state.ab_results_b:
                ab_comp1, ab_comp2 = st.columns(2)
                with ab_comp1:
                    st.markdown("##### 📋 JD A Rankings")
                    for i, c in enumerate(ranked, 1):
                        st.markdown(f"**#{i}** {c['filename']} — **{c['score']:.0%}**")
                with ab_comp2:
                    st.markdown("##### 📋 JD B Rankings")
                    for i, c in enumerate(st.session_state.ab_results_b, 1):
                        st.markdown(f"**#{i}** {c['filename']} — **{c['score']:.0%}**")
        else:
            candidate_names = [c['filename'] for c in ranked]
            selected = st.multiselect("Select 2-4 candidates to compare", candidate_names,
                default=candidate_names[:min(2, len(candidate_names))], max_selections=4)

            if len(selected) >= 2:
                selected_candidates = [c for c in ranked if c['filename'] in selected]

                st.markdown("#### 📋 Comparison Table")
                comp_data = {'Attribute': ['📧 Email', '📞 Phone', '🎓 Education', '💼 Experience',
                    '🎯 Overall', '📝 Content', '🔧 Skills', '📐 Format', '💼 Exp Score',
                    '🎓 Edu Score', '🤝 Culture Fit', '🏷️ Skills Count', '✅ Keywords Matched']}
                for c in selected_candidates:
                    comp_data[c['filename']] = [
                        c['email'], c['phone'], c['education'], f"{c['experience_years']} yrs",
                        f"{c['score']:.0%}", f"{c['content_score']:.0%}", f"{c['skill_score']:.0%}",
                        f"{c['formatting_score']:.0%}", f"{c['experience_score']:.0%}",
                        f"{c['education_score']:.0%}", f"{c.get('culture_fit_score', 0):.0%}",
                        str(len(c['skills'])), str(len(c['matched_keywords']))]
                st.dataframe(pd.DataFrame(comp_data).set_index('Attribute'), use_container_width=True, height=500)

                st.markdown("#### 🕸️ Radar Comparison")
                fig_compare = go.Figure()
                colors_list = ['#667eea', '#f093fb', '#48bb78', '#ecc94b']
                cats_c = ['Content', 'Skills', 'Format', 'Experience', 'Education', 'Culture Fit']
                for i, c in enumerate(selected_candidates):
                    vals = [c['content_score'], c['skill_score'], c['formatting_score'],
                            c['experience_score'], c['education_score'], c.get('culture_fit_score', 0)]
                    color = colors_list[i % len(colors_list)]
                    fig_compare.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=cats_c + [cats_c[0]],
                        fill='toself', fillcolor=f'{color}1a', line=dict(color=color, width=2),
                        marker=dict(size=6), name=c['filename'][:25]))
                fig_compare.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)',
                    radialaxis=dict(range=[0,1], gridcolor='rgba(255,255,255,0.1)', tickformat='.0%'),
                    angularaxis=dict(gridcolor='rgba(255,255,255,0.1)')),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a0aec0', family='Inter'), margin=dict(l=60,r=60,t=30,b=30), height=400,
                    legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)))
                st.plotly_chart(fig_compare, use_container_width=True)

                st.markdown("#### 🔧 Skills Comparison")
                all_cand_skills = set()
                for c in selected_candidates:
                    all_cand_skills.update(c['skills'])
                if all_cand_skills:
                    skills_matrix = [{'Skill': skill, **{c['filename'][:25]: ('✅' if skill in c['skills'] else '❌') for c in selected_candidates}} for skill in sorted(all_cand_skills)]
                    st.dataframe(pd.DataFrame(skills_matrix).set_index('Skill'), use_container_width=True)
            elif len(selected) == 1:
                st.warning("Please select at least 2 candidates to compare.")
    else:
        st.markdown("""<div style="text-align:center;padding:4rem 2rem;color:#a0aec0;">
            <h3>🔄 No candidates to compare</h3><p>Go to the <b>Analysis</b> tab first.</p></div>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━ TAB 4: EMAIL ━━━━━━━━━━━━
with tab4:
    st.markdown('<div class="section-header">📧 Automated Email Sender</div>', unsafe_allow_html=True)
    if st.session_state.ranked_results:
        ranked = st.session_state.ranked_results
        e1, e2 = st.columns(2)
        with e1:
            company_name = st.text_input("🏢 Company Name", placeholder="e.g., Google")
        with e2:
            hiring_manager = st.text_input("👤 Hiring Manager", placeholder="e.g., John Smith")

        threshold = st.slider("🎯 Qualification Threshold", 0.0, 1.0, 0.5, 0.05)
        notify_recruiter = st.checkbox("🔔 Send summary notification to recruiter", key="notify_rec")
        recruiter_email = ""
        if notify_recruiter:
            recruiter_email = st.text_input("Recruiter email", placeholder="recruiter@company.com", key="rec_email")

        st.markdown("#### 📋 Candidate Preview")
        preview = [{'Candidate': c['filename'], 'Email': c['email'], 'Score': f"{c['score']:.0%}",
            'Status': "✅ Qualified" if c['score'] >= threshold else "❌ Not Qualified"} for c in ranked]
        st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

        q_count = sum(1 for c in ranked if c['score'] >= threshold)
        st.markdown(f"**{q_count}** qualified · **{len(ranked)-q_count}** not qualified at **{threshold:.0%}**")
        st.markdown("---")

        _, send_col, _ = st.columns([1, 1, 1])
        with send_col:
            send_btn = st.button("📨 Send Emails to All", use_container_width=True, type="primary")

        if send_btn:
            if not company_name or not hiring_manager:
                st.error("Please enter company name and hiring manager.")
            else:
                email_progress = st.progress(0)
                results_log = []
                for i, candidate in enumerate(ranked):
                    if candidate['email'] == "No email found":
                        results_log.append(f"⚠️ Skipped {candidate['filename']} — no email")
                        continue
                    q = candidate['score'] >= threshold
                    with st.spinner(f"Generating email for {candidate['filename']}..."):
                        email_body = generate_email_with_gemini("Job Application Status",
                            candidate['filename'].replace('.pdf','').replace('.docx','').replace('.txt',''),
                            company_name, hiring_manager, candidate['filename'], candidate['score'],
                            candidate['skills'], q)
                    if email_body:
                        success = send_email(candidate['email'], "Job Application Status", email_body)
                        results_log.append(f"{'✅' if success else '❌'} {'Sent to' if success else 'Failed:'} {candidate['email']}")
                    else:
                        results_log.append(f"❌ Failed to generate email for {candidate['filename']}")
                    email_progress.progress((i + 1) / len(ranked))
                email_progress.empty()

                # Send recruiter notification
                if notify_recruiter and recruiter_email and recruiter_email.strip():
                    summary = f"Resume Screening Summary\n\nTotal Candidates: {len(ranked)}\nQualified: {q_count}\n\nTop Candidates:\n"
                    for i, c in enumerate(ranked[:5], 1):
                        summary += f"{i}. {c['filename']} — {c['score']:.0%}\n"
                    send_email(recruiter_email, f"Screening Summary - {company_name}", summary)
                    results_log.append(f"📬 Summary sent to recruiter: {recruiter_email}")

                st.markdown("#### 📬 Email Results")
                for log in results_log:
                    st.markdown(log)

        # Email Templates Section
        st.markdown('<div class="section-header">📋 Email Templates</div>', unsafe_allow_html=True)
        st.markdown("Create and edit reusable templates. Use `{name}`, `{company}`, `{score}`, `{manager}` as placeholders.")
        templates = st.session_state.email_templates

        tmpl_tabs = st.tabs(list(templates.keys()) + ["➕ New Template"])
        for i, (tname, tbody) in enumerate(templates.items()):
            with tmpl_tabs[i]:
                edited = st.text_area(f"Edit {tname} template", value=tbody, height=150, key=f"tmpl_{i}")
                if edited != tbody:
                    st.session_state.email_templates[tname] = edited
                    st.caption("✅ Template auto-saved")

        with tmpl_tabs[-1]:
            new_name = st.text_input("Template name", placeholder="e.g., Interview Invite", key="new_tmpl_name")
            new_body = st.text_area("Template body", height=120, placeholder="Dear {name},\n\n...", key="new_tmpl_body")
            if st.button("💾 Save Template", key="save_tmpl") and new_name and new_body:
                st.session_state.email_templates[new_name] = new_body
                st.success(f"Template '{new_name}' saved!")
                st.rerun()
    else:
        st.markdown("""<div style="text-align:center;padding:4rem 2rem;color:#a0aec0;">
            <h3>📧 No candidates to email</h3><p>Go to <b>Analysis</b> tab first.</p></div>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━ TAB 5: AI CHAT ━━━━━━━━━━━━
with tab5:
    st.markdown('<div class="section-header">🤖 AI Recruiting Assistant</div>', unsafe_allow_html=True)
    if st.session_state.ranked_results:
        st.markdown("Ask me anything about the analyzed candidates!")

        # Display chat history
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f'<div class="chat-msg-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-msg-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

        # Chat input
        chat_input = st.text_input("Ask a question...", placeholder="e.g., Who has the most Python experience?", key="chat_input")
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            chat_btn = st.button("💬 Ask", key="chat_btn", type="primary")
        with c2:
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

        if chat_btn and chat_input:
            st.session_state.chat_history.append({'role': 'user', 'content': chat_input})
            with st.spinner("Thinking..."):
                response = ai_chat_response(chat_input, st.session_state.ranked_results,
                    st.session_state.job_description)
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            st.rerun()

        # Quick questions
        st.markdown("---")
        st.markdown("**💡 Quick Questions:**")
        quick_qs = ["Who is the best candidate and why?", "Which candidates lack critical skills?",
            "Compare the top 3 candidates", "What skills are most common?",
            "Who has the best culture fit?", "Any bias concerns in the resumes?"]
        cols = st.columns(3)
        for i, q in enumerate(quick_qs):
            with cols[i % 3]:
                if st.button(q, key=f"qq_{i}"):
                    st.session_state.chat_history.append({'role': 'user', 'content': q})
                    with st.spinner("Thinking..."):
                        response = ai_chat_response(q, st.session_state.ranked_results,
                            st.session_state.job_description)
                    st.session_state.chat_history.append({'role': 'assistant', 'content': response})
                    st.rerun()
    else:
        st.markdown("""<div style="text-align:center;padding:4rem 2rem;color:#a0aec0;">
            <h3>🤖 No candidates to chat about</h3><p>Analyze resumes first in the <b>Analysis</b> tab.</p></div>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━ TAB 6: TRENDS ━━━━━━━━━━━━
with tab6:
    st.markdown('<div class="section-header">📈 Historical Trends</div>', unsafe_allow_html=True)
    if st.session_state.authenticated:
        sessions = get_all_sessions_for_trends(st.session_state.user['id'])
        if sessions and len(sessions) >= 2:
            dates = [s['created_at'][:10] for s in sessions]
            avg_scores = [s['avg_score'] for s in sessions]
            top_scores = [s['top_score'] for s in sessions]
            counts = [s['candidate_count'] for s in sessions]

            t1, t2 = st.columns(2)
            with t1:
                st.markdown("#### 📊 Score Trends Over Time")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=dates, y=avg_scores, name='Avg Score',
                    line=dict(color='#667eea', width=2), marker=dict(size=8)))
                fig_trend.add_trace(go.Scatter(x=dates, y=top_scores, name='Top Score',
                    line=dict(color='#48bb78', width=2), marker=dict(size=8)))
                fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a0aec0', family='Inter'), yaxis=dict(tickformat='.0%', range=[0,1]),
                    margin=dict(l=10,r=10,t=10,b=10), height=300,
                    legend=dict(bgcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig_trend, use_container_width=True)

            with t2:
                st.markdown("#### 👥 Candidates Per Session")
                fig_count = go.Figure()
                fig_count.add_trace(go.Bar(x=dates, y=counts,
                    marker=dict(color='#764ba2', line=dict(width=0)),
                    text=counts, textposition='outside', textfont=dict(color='#a0aec0')))
                fig_count.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a0aec0', family='Inter'),
                    margin=dict(l=10,r=10,t=10,b=10), height=300)
                st.plotly_chart(fig_count, use_container_width=True)

            # Session details table
            st.markdown("#### 📋 Session History")
            session_table = [{'Date': s['created_at'][:16], 'Name': s['session_name'],
                'Candidates': s['candidate_count'], 'Avg Score': f"{s['avg_score']:.0%}",
                'Top Score': f"{s['top_score']:.0%}"} for s in sessions]
            st.dataframe(pd.DataFrame(session_table), use_container_width=True, hide_index=True)
        else:
            st.info("📊 Run at least 2 analysis sessions to see trends. Current sessions will appear here automatically.")
    else:
        st.markdown("""<div style="text-align:center;padding:4rem 2rem;color:#a0aec0;">
            <h3>📈 Login to view trends</h3>
            <p>Sign in from the sidebar to track your screening history and view trend analytics.</p></div>""", unsafe_allow_html=True)