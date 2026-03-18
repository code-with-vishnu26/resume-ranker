# resume_ranker.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from resume_parser import (
    extract_skills, extract_experience, extract_education,
    extract_soft_skills, detect_bias_indicators
)


def calculate_skill_match_score(resume_skills, job_skills):
    """Calculate skill match score between resume and job description."""
    if not job_skills:
        return 0
    matches = sum(1 for skill in resume_skills if skill in job_skills)
    return matches / len(job_skills)


def calculate_formatting_score(text):
    """Score resume formatting quality (0-1)."""
    score = 0
    checks = 0

    section_keywords = [
        'experience', 'education', 'skills', 'projects', 'summary',
        'objective', 'certifications', 'achievements', 'awards',
        'publications', 'interests', 'references', 'profile'
    ]
    sections_found = sum(1 for kw in section_keywords if kw in text.lower())
    score += min(sections_found / 4, 1.0)
    checks += 1

    word_count = len(text.split())
    if 200 <= word_count <= 1500:
        score += 1.0
    elif 100 <= word_count < 200 or 1500 < word_count <= 2000:
        score += 0.6
    elif word_count > 0:
        score += 0.3
    checks += 1

    has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
    contact_score = (int(has_email) + int(has_phone)) / 2
    score += contact_score
    checks += 1

    return score / checks if checks > 0 else 0


def calculate_experience_score(experience_years, job_description):
    """Score experience relevance (0-1)."""
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',
        r'minimum\s*(\d+)\s*(?:years?|yrs?)',
        r'at\s*least\s*(\d+)\s*(?:years?|yrs?)',
    ]
    required_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, job_description.lower())
        if matches:
            required_years = int(matches[0])
            break

    if required_years == 0:
        if experience_years >= 5:
            return 1.0
        elif experience_years >= 3:
            return 0.8
        elif experience_years >= 1:
            return 0.6
        else:
            return 0.3

    if experience_years >= required_years:
        return 1.0
    elif experience_years >= required_years * 0.7:
        return 0.7
    elif experience_years >= required_years * 0.5:
        return 0.5
    else:
        return 0.2


def calculate_education_score(education_level, job_description):
    """Score education fit (0-1)."""
    jd_lower = job_description.lower()

    education_rank = {
        'PhD': 5, 'MBA': 4, "Master's": 4, "Bachelor's": 3,
        'Diploma': 2, 'Associate': 1, 'High School': 0, 'Not specified': 0,
    }

    candidate_rank = education_rank.get(education_level, 0)

    required_rank = 0
    if 'phd' in jd_lower or 'doctorate' in jd_lower:
        required_rank = 5
    elif "master" in jd_lower or 'mba' in jd_lower:
        required_rank = 4
    elif 'bachelor' in jd_lower or 'degree' in jd_lower:
        required_rank = 3
    elif 'diploma' in jd_lower:
        required_rank = 2

    if required_rank == 0:
        return min(candidate_rank / 3, 1.0)

    if candidate_rank >= required_rank:
        return 1.0
    elif candidate_rank >= required_rank - 1:
        return 0.6
    else:
        return 0.3


def calculate_culture_fit_score(resume_text, job_description):
    """Score culture fit based on soft skills alignment (0-1)."""
    resume_soft = extract_soft_skills(resume_text)
    jd_soft = extract_soft_skills(job_description)

    if not jd_soft:
        # If JD doesn't mention soft skills, score based on presence alone
        return min(len(resume_soft) / 5, 1.0) if resume_soft else 0.3

    matching = sum(1 for s in resume_soft if s in jd_soft)
    score = matching / len(jd_soft) if jd_soft else 0

    # Bonus for having multiple soft skills even if not in JD
    bonus = min(len(resume_soft) * 0.05, 0.2)

    return min(score + bonus, 1.0)


def get_keyword_analysis(resume_text, job_description):
    """Get matched and missing keywords between resume and JD."""
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=40)
        vectorizer.fit([job_description])
        jd_keywords = set(vectorizer.get_feature_names_out())
    except Exception:
        jd_keywords = set()

    resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))

    matched = sorted(jd_keywords.intersection(resume_words))
    missing = sorted(jd_keywords - resume_words)

    return matched, missing


def rank_resumes(resumes, job_description, custom_skills=None, weights=None):
    """Rank resumes with detailed ATS-style breakdown."""
    job_skills = extract_skills(job_description, custom_skills)
    documents = [job_description] + [resume['text'] for resume in resumes]

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)
    cos_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

    # Default weights
    if weights is None:
        weights = {
            'content': 0.25,
            'skill': 0.25,
            'formatting': 0.10,
            'experience': 0.15,
            'education': 0.10,
            'culture_fit': 0.15,
        }

    ranked_candidates = []
    for idx, resume in enumerate(resumes):
        resume_text = resume['text']
        resume_skills = extract_skills(resume_text, custom_skills)
        experience_years = extract_experience(resume_text)
        education_level = extract_education(resume_text)
        soft_skills = extract_soft_skills(resume_text)
        bias_flags = detect_bias_indicators(resume_text)

        # Individual scores
        content_score = float(cos_similarities[0][idx])
        skill_score = calculate_skill_match_score(resume_skills, job_skills)
        formatting_score = calculate_formatting_score(resume_text)
        experience_score = calculate_experience_score(experience_years, job_description)
        education_score = calculate_education_score(education_level, job_description)
        culture_fit_score = calculate_culture_fit_score(resume_text, job_description)

        # Keyword analysis
        matched_kw, missing_kw = get_keyword_analysis(resume_text, job_description)

        # Weighted overall score
        overall_score = (
            weights.get('content', 0.25) * content_score +
            weights.get('skill', 0.25) * skill_score +
            weights.get('formatting', 0.10) * formatting_score +
            weights.get('experience', 0.15) * experience_score +
            weights.get('education', 0.10) * education_score +
            weights.get('culture_fit', 0.15) * culture_fit_score
        )

        ranked_candidates.append({
            'filename': resume['filename'],
            'email': resume['email'],
            'phone': resume.get('phone', 'N/A'),
            'text': resume.get('text', ''),
            'score': overall_score,
            'content_score': content_score,
            'skill_score': skill_score,
            'formatting_score': formatting_score,
            'experience_score': experience_score,
            'education_score': education_score,
            'culture_fit_score': culture_fit_score,
            'skills': resume_skills,
            'soft_skills': soft_skills,
            'experience_years': experience_years,
            'education': education_level,
            'matched_keywords': matched_kw,
            'missing_keywords': missing_kw,
            'bias_flags': bias_flags,
        })

    ranked_candidates.sort(key=lambda x: x['score'], reverse=True)
    return ranked_candidates