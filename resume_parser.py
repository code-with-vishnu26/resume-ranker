# resume_parser.py
import PyPDF2
import re
import os
import zipfile
import tempfile


def extract_text_from_resume(file_path):
    """Extract text from PDF, DOCX, or TXT resume."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return _extract_from_pdf(file_path)
    elif ext == '.docx':
        return _extract_from_docx(file_path)
    elif ext == '.txt':
        return _extract_from_txt(file_path)
    else:
        return ""


def _extract_from_pdf(pdf_path):
    """Extract text from PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {str(e)}")
    return text


def _extract_from_docx(docx_path):
    """Extract text from DOCX file."""
    try:
        import docx
        doc = docx.Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting text from {docx_path}: {str(e)}")
        return ""


def _extract_from_txt(txt_path):
    """Extract text from TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Error extracting text from {txt_path}: {str(e)}")
        return ""


def extract_email(text):
    """Extract email address from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else "No email found"


def extract_phone(text):
    """Extract phone number from text."""
    phone_patterns = [
        r'[\+]?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{10}',
    ]
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            phone = phones[0].strip()
            if len(phone) >= 10:
                return phone
    return "No phone found"


def extract_experience(text):
    """Extract years of experience from resume text."""
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',
        r'experience\s*(?:of)?\s*(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:in|of)\s*\w+',
        r'(\d+)\+?\s*years?\s*(?:professional|industry|work)',
    ]
    max_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        for match in matches:
            years = int(match)
            if 0 < years < 50:
                max_years = max(max_years, years)
    return max_years


def extract_education(text):
    """Extract highest education level from resume text."""
    text_lower = text.lower()
    education_levels = {
        'phd': 'PhD',
        'ph.d': 'PhD',
        'doctorate': 'PhD',
        'master': "Master's",
        "master's": "Master's",
        'mba': "MBA",
        'm.s.': "Master's",
        'm.s ': "Master's",
        'm.tech': "Master's",
        'mtech': "Master's",
        'ms in': "Master's",
        'bachelor': "Bachelor's",
        "bachelor's": "Bachelor's",
        'b.tech': "Bachelor's",
        'btech': "Bachelor's",
        'b.s.': "Bachelor's",
        'b.s ': "Bachelor's",
        'b.e.': "Bachelor's",
        'b.sc': "Bachelor's",
        'bs in': "Bachelor's",
        'diploma': 'Diploma',
        'associate': 'Associate',
        'high school': 'High School',
    }

    found = set()
    for keyword, level in education_levels.items():
        if keyword in text_lower:
            found.add(level)

    priority = ['PhD', 'MBA', "Master's", "Bachelor's", 'Diploma', 'Associate', 'High School']
    for level in priority:
        if level in found:
            return level
    return "Not specified"


def extract_skills(text, custom_skills=None):
    """Extract skills from text against a comprehensive skill list."""
    common_skills = [
        "python", "java", "javascript", "typescript", "html", "css", "sql",
        "react", "angular", "vue", "node.js", "express.js", "django", "flask",
        "streamlit", "fastapi", "spring boot",
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
        "machine learning", "deep learning", "artificial intelligence",
        "natural language processing", "nlp", "computer vision",
        "data analysis", "data science", "data engineering",
        "tensorflow", "pytorch", "scikit-learn", "keras", "opencv",
        "pandas", "numpy", "matplotlib", "seaborn", "plotly",
        "mongodb", "postgresql", "mysql", "redis", "elasticsearch",
        "git", "github", "gitlab", "ci/cd", "jenkins",
        "linux", "devops", "microservices", "restful apis", "graphql",
        "web scraping", "selenium", "beautifulsoup",
        "power bi", "tableau", "excel", "r programming",
        "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin",
        "agile", "scrum", "project management", "jira",
        "communication", "leadership", "problem solving", "teamwork",
        "yolo", "transfer learning", "openai", "langchain", "llm",
        "web development", "full stack", "frontend", "backend",
        "api development", "database management", "cloud computing",
    ]

    # Add custom skills if provided
    if custom_skills:
        for s in custom_skills:
            skill_name = s.get('name', s) if isinstance(s, dict) else s
            if skill_name.lower() not in common_skills:
                common_skills.append(skill_name.lower())

    skills_found = []
    text_lower = text.lower()

    for skill in common_skills:
        if skill in text_lower:
            skills_found.append(skill)

    return list(set(skills_found))


# ─── Multi-Language Support ───
def detect_language(text):
    """Detect the language of resume text."""
    try:
        from deep_translator import single_detection
        # Simple heuristic: check for non-ASCII characters ratio
        non_ascii = sum(1 for c in text if ord(c) > 127)
        total = len(text) if text else 1
        if non_ascii / total > 0.3:
            return "non-english"
        return "english"
    except Exception:
        return "english"


def translate_text(text, target='en'):
    """Translate text to English using deep-translator."""
    try:
        from deep_translator import GoogleTranslator
        # Split into chunks (Google Translate limit ~5000 chars)
        chunks = [text[i:i+4500] for i in range(0, len(text), 4500)]
        translated = ""
        for chunk in chunks:
            result = GoogleTranslator(source='auto', target=target).translate(chunk)
            translated += result + " "
        return translated.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text


# ─── Batch Processing ───
def extract_resumes_from_zip(zip_file_path):
    """Extract all resume files from a ZIP archive."""
    extracted_files = []
    supported_extensions = ('.pdf', '.docx', '.txt')

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as z:
            temp_dir = tempfile.mkdtemp()
            for file_info in z.infolist():
                if file_info.filename.startswith('__MACOSX') or file_info.filename.startswith('.'):
                    continue
                if file_info.filename.lower().endswith(supported_extensions):
                    extracted_path = z.extract(file_info, temp_dir)
                    extracted_files.append({
                        'path': extracted_path,
                        'name': os.path.basename(file_info.filename),
                    })
    except Exception as e:
        print(f"Error extracting ZIP: {e}")

    return extracted_files


# ─── LinkedIn Profile Parser ───
def extract_from_linkedin_url(url):
    """Attempt to extract profile text from a LinkedIn URL."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract visible text
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator='\n', strip=True)
            return text[:5000]
        else:
            return None
    except Exception as e:
        print(f"LinkedIn extraction error: {e}")
        return None


def parse_linkedin_text(text):
    """Parse manually pasted LinkedIn profile text."""
    if not text:
        return None

    result = {
        'text': text,
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'education': extract_education(text),
        'experience_years': extract_experience(text),
    }
    return result


# ─── Soft Skills Extraction (for Culture Fit) ───
SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "collaboration",
    "problem solving", "critical thinking", "creativity", "innovation",
    "adaptability", "flexibility", "time management", "organization",
    "decision making", "conflict resolution", "negotiation",
    "emotional intelligence", "empathy", "mentoring", "coaching",
    "public speaking", "presentation", "writing", "interpersonal",
    "self-motivated", "initiative", "proactive", "detail-oriented",
    "strategic thinking", "analytical", "customer service", "multitasking",
]


def extract_soft_skills(text):
    """Extract soft skills from resume text."""
    text_lower = text.lower()
    found = [skill for skill in SOFT_SKILLS if skill in text_lower]
    return list(set(found))


# ─── Bias Detection Keywords ───
BIAS_INDICATORS = {
    'age': [
        'young', 'energetic', 'digital native', 'recent graduate',
        'mature', 'seasoned', 'veteran'
    ],
    'gender': [
        'he ', 'she ', ' his ', ' her ', 'businessman', 'businesswoman',
        'chairman', 'chairwoman', 'manpower'
    ],
    'appearance': [
        'photo', 'photograph', 'attractive', 'height', 'weight'
    ],
    'personal': [
        'marital status', 'married', 'single', 'children',
        'date of birth', 'age:', 'religion', 'nationality'
    ]
}


def detect_bias_indicators(text):
    """Detect potential bias indicators in resume text."""
    text_lower = text.lower()
    found_biases = {}

    for category, keywords in BIAS_INDICATORS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        if matches:
            found_biases[category] = matches

    return found_biases


# ─── Resume Anonymizer ───
def anonymize_resume(text):
    """Remove identifying information from resume text for blind hiring."""
    anonymized = text

    # Remove emails
    anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]', anonymized)

    # Remove phone numbers
    phone_patterns = [
        r'[\+]?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    ]
    for pattern in phone_patterns:
        anonymized = re.sub(pattern, '[PHONE REDACTED]', anonymized)

    # Remove URLs (LinkedIn, GitHub, personal websites)
    anonymized = re.sub(r'https?://\S+', '[URL REDACTED]', anonymized)
    anonymized = re.sub(r'www\.\S+', '[URL REDACTED]', anonymized)

    # Remove gender pronouns and gendered terms
    gender_terms = {
        r'\bhe\b': 'they', r'\bshe\b': 'they',
        r'\bhis\b': 'their', r'\bher\b': 'their',
        r'\bhim\b': 'them', r'\bhimself\b': 'themselves',
        r'\bherself\b': 'themselves',
        r'\bMr\.?\b': '', r'\bMrs\.?\b': '', r'\bMs\.?\b': '',
        r'\bSir\b': '', r'\bMadam\b': '',
    }
    for pattern, replacement in gender_terms.items():
        anonymized = re.sub(pattern, replacement, anonymized, flags=re.IGNORECASE)

    # Remove personal info patterns
    anonymized = re.sub(r'(?i)date\s*of\s*birth[:\s]*\S+', '[DOB REDACTED]', anonymized)
    anonymized = re.sub(r'(?i)age[:\s]*\d+', '[AGE REDACTED]', anonymized)
    anonymized = re.sub(r'(?i)marital\s*status[:\s]*\w+', '[STATUS REDACTED]', anonymized)
    anonymized = re.sub(r'(?i)nationality[:\s]*\w+', '[NATIONALITY REDACTED]', anonymized)
    anonymized = re.sub(r'(?i)religion[:\s]*\w+', '[RELIGION REDACTED]', anonymized)

    # Remove addresses (basic pattern)
    anonymized = re.sub(r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\.?',
                        '[ADDRESS REDACTED]', anonymized, flags=re.IGNORECASE)

    # Remove the first line (usually candidate name)
    lines = anonymized.split('\n')
    if lines and len(lines[0].split()) <= 4:
        lines[0] = '[NAME REDACTED]'
    anonymized = '\n'.join(lines)

    return anonymized