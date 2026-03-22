import re

import pdfplumber
import streamlit as st

try:
    import argostranslate.translate
except ImportError:
    argostranslate = None

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


def inject_custom_css():
    """Add neutral card styling so Streamlit theme works in light and dark mode."""
    st.markdown(
        """
        <style>
        .app-header {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 16px;
        }
        .app-title {
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
        }
        .app-subtitle {
            font-size: 1rem;
            margin-top: 8px;
            opacity: 0.8;
        }
        .section-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 18px;
        }
        .card-heading {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 12px;
        }
        .decision-allowed,
        .decision-dismissed,
        .decision-neutral {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 10px;
            padding: 12px 14px;
            font-weight: 600;
        }
        .amount-box {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 10px;
            padding: 12px 14px;
            font-weight: 600;
        }
        .answer-box {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            padding: 14px 16px;
        }
        .helper-text {
            opacity: 0.8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def open_card(title):
    """Open a styled card section."""
    st.markdown(
        f'<div class="section-card"><div class="card-heading">{title}</div>',
        unsafe_allow_html=True,
    )


def close_card():
    """Close a styled card section."""
    st.markdown("</div>", unsafe_allow_html=True)


def extract_text_from_pdf(file):
    """Extract text from every page in an uploaded PDF file."""
    extracted_pages = []

    try:
        with pdfplumber.open(file) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()

                if page_text and page_text.strip():
                    extracted_pages.append(f"Page {page_number}\n{page_text}")
                else:
                    extracted_pages.append(f"Page {page_number}\n[No text found on this page]")

        if extracted_pages:
            return "\n\n".join(extracted_pages)
        return "No pages were found in the PDF."

    except Exception as error:
        raise ValueError(f"Unable to read the PDF file. Details: {error}") from error


def normalize_text(text):
    """Normalize text so matching works better across different document formats."""
    if not text:
        return ""

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_text = re.sub(r"[ \t]+", " ", normalized_text)
    normalized_text = re.sub(r"\n\s*\n+", "\n\n", normalized_text)
    return normalized_text.strip()


def unique_preserve_order(items):
    """Return unique items while keeping the original order."""
    unique_items = []
    seen = set()

    for item in items:
        cleaned_item = item.strip()
        lowered_item = cleaned_item.lower()

        if cleaned_item and lowered_item not in seen:
            unique_items.append(cleaned_item)
            seen.add(lowered_item)

    return unique_items


def format_bullet_list(items):
    """Format a list as markdown bullets for cleaner Streamlit display."""
    if not items or items == ["Not Found"]:
        return "Not Found"
    return "\n".join(f"- {item}" for item in items)


def highlight_keyword(text, keyword):
    """Highlight a keyword using markdown bold markers."""
    if not keyword:
        return text

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda match: f"**{match.group(0)}**", text)


def search_in_document(text, keyword):
    """Return document lines that contain the given keyword."""
    normalized_text = normalize_text(text)
    cleaned_keyword = keyword.strip()

    if not cleaned_keyword:
        return []

    matching_lines = []
    for line in normalized_text.splitlines():
        cleaned_line = line.strip()
        if cleaned_line and cleaned_keyword.lower() in cleaned_line.lower():
            matching_lines.append(highlight_keyword(cleaned_line, cleaned_keyword))

    return matching_lines


def render_summary(summary):
    """Return markdown text for the full structured summary."""
    return "\n\n".join(
        [
            "#### Case Overview\n"
            + "\n".join(f"- {line}" for line in summary["case_overview"].splitlines()),
            f"#### Core Issue\n{summary['core_issue']}",
            f"#### Key Arguments\n{format_bullet_list(summary['key_arguments'])}",
            f"#### Amount Involved\n{summary['amount_involved']}",
            f"#### Final Decision\n{summary['final_decision']}",
            f"#### Legal References\n{format_bullet_list(summary['legal_references'])}",
        ]
    )


def render_filtered_view(summary, view_mode):
    """Return markdown text for the selected summary view."""
    if view_mode == "Hide Summary":
        return "Summary hidden"

    if view_mode == "Only Final Decision":
        return f"#### Final Decision\n{summary['final_decision']}"

    if view_mode == "Only Financial Information":
        return f"#### Amount Involved\n{summary['amount_involved']}"

    return render_summary(summary)


def get_english_to_hindi_translation():
    """Load the locally installed English to Hindi Argos Translate model."""
    if argostranslate is None:
        return None

    try:
        installed_languages = argostranslate.translate.get_installed_languages()
        english_language = next((language for language in installed_languages if language.code == "en"), None)
        hindi_language = next((language for language in installed_languages if language.code == "hi"), None)

        if english_language and hindi_language:
            return english_language.get_translation(hindi_language)
    except Exception:
        return None

    return None


def translate_to_hindi(text):
    """Translate English text into Hindi using a local Argos Translate model."""
    if not text or text == "Not Found":
        return text

    translation = get_english_to_hindi_translation()
    if translation is None:
        return "Translation not available"

    try:
        return translation.translate(text)
    except Exception:
        return "Translation not available"


def translate_summary_to_hindi(summary):
    """Translate only the structured summary content into Hindi."""
    return {
        "case_overview": translate_to_hindi(summary["case_overview"]),
        "core_issue": translate_to_hindi(summary["core_issue"]),
        "key_arguments": [translate_to_hindi(item) for item in summary["key_arguments"]],
        "amount_involved": translate_to_hindi(summary["amount_involved"]),
        "final_decision": translate_to_hindi(summary["final_decision"]),
        "legal_references": [translate_to_hindi(item) for item in summary["legal_references"]],
    }


@st.cache_resource
def load_qa_pipeline():
    """Load the HuggingFace question-answering pipeline only once."""
    if pipeline is None:
        return None

    try:
        return pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
    except Exception:
        return None


def keyword_based_answer(question, extracted_data):
    """Return a simple fallback answer based on question keywords."""
    lowered_question = question.lower()

    if "amount" in lowered_question or "penalty" in lowered_question or "financial" in lowered_question:
        return f"Amounts: {', '.join(extracted_data['amounts'])}"

    if "decision" in lowered_question or "result" in lowered_question or "outcome" in lowered_question:
        return f"Final Decision: {extracted_data['final_decision']}"

    if "date" in lowered_question or "hearing" in lowered_question:
        return f"Dates: {', '.join(extracted_data['dates'])}"

    return None


def answer_question(question, context, extracted_data):
    """Answer a question using rule-based answers first, then the QA model if needed."""
    cleaned_question = question.strip()
    lowered_question = cleaned_question.lower()

    if not cleaned_question:
        return "Enter a question to get started"

    if "decision" in lowered_question:
        return extracted_data["final_decision"]

    if "amount" in lowered_question:
        return ", ".join(extracted_data["amounts"])

    if "date" in lowered_question:
        return ", ".join(extracted_data["dates"])

    cleaned_context = normalize_text(context).lower()[:1000]

    qa_pipeline = load_qa_pipeline()
    if qa_pipeline is None:
        return "Could not find a precise answer. Try rephrasing your question."

    try:
        result = qa_pipeline(question=lowered_question, context=cleaned_context)
        answer = result.get("answer", "").strip()
        score = result.get("score", 0.0)

        if score < 0.2 or not answer:
            return "Could not find a precise answer. Try rephrasing your question."

        return answer
    except Exception:
        return "Could not find a precise answer. Try rephrasing your question."


def extract_case_number(text):
    """Extract a case number using multiple common legal labels."""
    normalized_text = normalize_text(text)

    patterns = [
        r"\b(?:appeal|case|order|file)\s*no\.?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/().\- ]{0,100})",
        r"\b(?:appeal|case|order|file)\s*number\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/().\- ]{0,100})",
    ]

    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
            value = match.group(1).strip(" .,:;-")
            value = re.split(r"\n", value)[0].strip()
            if value:
                matches.append(value)

    unique_matches = unique_preserve_order(matches)
    return unique_matches[0] if unique_matches else "Not Found"


def extract_dates(text):
    """Extract dates in multiple common legal-document formats."""
    normalized_text = normalize_text(text)

    month_names = (
        "January|February|March|April|May|June|July|August|September|"
        "October|November|December"
    )

    patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",
        rf"\b\d{{1,2}}\s+(?:{month_names})\s+\d{{4}}\b",
        rf"\b(?:{month_names})\s+\d{{1,2}},\s+\d{{4}}\b",
    ]

    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, normalized_text, re.IGNORECASE))

    unique_dates = unique_preserve_order(matches)
    return unique_dates if unique_dates else ["Not Found"]


def extract_amounts(text):
    """Extract monetary amounts from the document text."""
    normalized_text = normalize_text(text)

    patterns = [
        r"\u20B9\s?\d[\d,]*(?:\.\d{1,2})?",
        r"\bINR\s?\d[\d,]*(?:\.\d{1,2})?\b",
        r"\bRs\.?\s?\d[\d,]*(?:\.\d{1,2})?\b",
        r"\b\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?\b",
    ]

    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, normalized_text, re.IGNORECASE))

    cleaned_amounts = [re.sub(r"\s+", " ", match).strip() for match in matches]
    unique_amounts = unique_preserve_order(cleaned_amounts)

    currency_values = {}
    for amount in unique_amounts:
        numeric_only = re.sub(r"^(?:\u20B9|INR|Rs\.?)\s*", "", amount, flags=re.IGNORECASE).strip()
        has_currency = bool(re.match(r"^(?:\u20B9|INR|Rs\.?)", amount, re.IGNORECASE))
        if has_currency:
            currency_values[numeric_only] = amount

    filtered_amounts = []
    for amount in unique_amounts:
        numeric_only = re.sub(r"^(?:\u20B9|INR|Rs\.?)\s*", "", amount, flags=re.IGNORECASE).strip()
        has_currency = bool(re.match(r"^(?:\u20B9|INR|Rs\.?)", amount, re.IGNORECASE))

        if has_currency:
            filtered_amounts.append(amount)
        elif numeric_only not in currency_values:
            filtered_amounts.append(amount)

    final_amounts = unique_preserve_order(filtered_amounts)
    return final_amounts if final_amounts else ["Not Found"]


def extract_final_decision(text):
    """Extract the final decision using broader keyword matching."""
    normalized_text = normalize_text(text).lower()

    partial_keywords = ["partly allowed", "partially allowed"]
    negative_keywords = ["dismissed", "rejected", "denied"]
    positive_keywords = ["appeal allowed", "allowed", "set aside", "succeeds"]

    for keyword in partial_keywords:
        if keyword in normalized_text:
            return "Partially Allowed"

    for keyword in negative_keywords:
        if keyword in normalized_text:
            return "Dismissed"

    for keyword in positive_keywords:
        if keyword in normalized_text:
            return "Allowed"

    return "Not Found"


def extract_party_names(text):
    """Extract party names from lines containing 'Versus' or 'vs'."""
    normalized_text = normalize_text(text)

    for line in normalized_text.splitlines():
        cleaned_line = line.strip()
        lowered_line = cleaned_line.lower()

        if " versus " in lowered_line or " vs " in lowered_line or " vs. " in lowered_line:
            return cleaned_line

    return "Not Found"


def extract_core_issue(text):
    """Extract the core issue from issue-related lines or early paragraphs."""
    normalized_text = normalize_text(text)
    paragraphs = [paragraph.strip() for paragraph in normalized_text.split("\n\n") if paragraph.strip()]

    issue_lines = []
    for line in normalized_text.splitlines():
        cleaned_line = line.strip()
        lowered_line = cleaned_line.lower()

        if any(keyword in lowered_line for keyword in ["issue", "matter", "dispute"]):
            issue_lines.append(cleaned_line)

    if issue_lines:
        return "\n".join(issue_lines[:2])

    meaningful_paragraphs = [paragraph for paragraph in paragraphs if not paragraph.lower().startswith("page ")]
    if meaningful_paragraphs:
        return "\n\n".join(meaningful_paragraphs[:2])

    return "Not Found"


def extract_key_arguments(text):
    """Extract lines containing common argument-related keywords."""
    normalized_text = normalize_text(text)
    argument_lines = []

    for line in normalized_text.splitlines():
        cleaned_line = line.strip()
        lowered_line = cleaned_line.lower()

        if any(keyword in lowered_line for keyword in ["argued", "submitted", "contended", "stated"]):
            argument_lines.append(cleaned_line)

    unique_arguments = unique_preserve_order(argument_lines)
    return unique_arguments if unique_arguments else ["Not Found"]


def extract_legal_references(text):
    """Extract legal references such as Section, Rule, Article, and Act names."""
    normalized_text = normalize_text(text)

    patterns = [
        r"\bSection\s+\d+[A-Za-z0-9()/-]*(?:\s+of\s+[A-Za-z][A-Za-z ]+(?:Act|Code|Law|Rules?))?\b",
        r"\bRule\s+\d+[A-Za-z0-9()/-]*(?:\s+of\s+[A-Za-z][A-Za-z ]+Rules?)?\b",
        r"\bArticle\s+\d+[A-Za-z0-9()/-]*\b",
    ]

    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, normalized_text, re.IGNORECASE))

    unique_references = unique_preserve_order(matches)
    return unique_references if unique_references else ["Not Found"]


def generate_structured_summary(text):
    """Generate a structured legal summary using rule-based extraction."""
    case_number = extract_case_number(text)
    dates = extract_dates(text)
    parties = extract_party_names(text)
    amounts = extract_amounts(text)
    final_decision = extract_final_decision(text)
    legal_references = extract_legal_references(text)

    return {
        "case_overview": "\n".join(
            [
                f"Case Number: {case_number}",
                f"Dates: {', '.join(dates)}",
                f"Parties: {parties}",
            ]
        ),
        "core_issue": extract_core_issue(text),
        "key_arguments": extract_key_arguments(text),
        "amount_involved": ", ".join(amounts),
        "final_decision": final_decision,
        "legal_references": legal_references,
    }


def render_decision_box(decision):
    """Render a colored final-decision box."""
    lowered_decision = decision.lower()

    if "allowed" in lowered_decision:
        css_class = "decision-allowed"
    elif "dismissed" in lowered_decision:
        css_class = "decision-dismissed"
    else:
        css_class = "decision-neutral"

    st.markdown(
        f'<div class="{css_class}">Final Decision: {decision}</div>',
        unsafe_allow_html=True,
    )


def render_amount_box(amounts):
    """Render a highlighted amount box."""
    st.markdown(
        f'<div class="amount-box">Amounts: {", ".join(amounts)}</div>',
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="AI Legal Document Assistant", layout="wide")
    inject_custom_css()

    st.markdown(
        """
        <div class="app-header">
            <div class="app-title">AI Legal Document Assistant</div>
            <div class="app-subtitle">Customs, Excise and Service Tax Appellate Tribunal (CESTAT)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        """This tool analyzes structured legal tribunal documents (like CESTAT orders).

It works best with:
- Clearly typed (not scanned) PDFs
- Documents containing case numbers, dates, and decisions

Features:
- Extracts key legal information
- Generates structured summary
- Allows keyword search
- Provides basic AI-based Q&A

Note:
Results may vary for highly unstructured or scanned documents."""
    )
    st.divider()

    language = st.radio("Language Selection", ["English", "Hindi"], horizontal=True)
    st.write("")

    uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

    if uploaded_file is None:
        st.info("Upload a PDF to begin.")
        return

    try:
        with st.spinner("Extracting text from PDF..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
            summary = generate_structured_summary(extracted_text)

        case_number = extract_case_number(extracted_text)
        dates = extract_dates(extracted_text)
        amounts = extract_amounts(extracted_text)
        final_decision = extract_final_decision(extracted_text)
        extracted_data = {
            "amounts": amounts,
            "dates": dates,
            "final_decision": final_decision,
        }

        if language == "Hindi":
            display_summary = translate_summary_to_hindi(summary)
        else:
            display_summary = summary

        open_card("Extracted Information")
        st.markdown(
            "\n".join(
                [
                    f"- **Case Number:** {case_number}",
                    f"- **Dates:** {', '.join(dates)}",
                    f"- **Parties:** {extract_party_names(extracted_text)}",
                ]
            )
        )
        st.write("")
        render_amount_box(amounts)
        st.write("")
        render_decision_box(final_decision)
        close_card()
        st.divider()

        st.markdown("### View Mode")
        view_mode = st.selectbox(
            "Choose how to view the summary",
            [
                "Full Summary",
                "Only Final Decision",
                "Only Financial Information",
                "Hide Summary",
            ],
        )
        st.write("")

        open_card("Structured Summary")
        st.markdown(render_filtered_view(display_summary, view_mode))
        close_card()
        st.divider()

        open_card("Search")
        search_keyword = st.text_input(
            "Search in document",
            placeholder="Search in document (e.g., penalty, tax, dismissed)",
        )
        st.markdown("### Search Results")
        if search_keyword.strip():
            search_results = search_in_document(extracted_text, search_keyword)
            if search_results:
                st.markdown("\n".join(f"- {line}" for line in search_results))
            else:
                st.write("No matching lines found.")
        else:
            st.markdown('<div class="helper-text">Enter a keyword to search</div>', unsafe_allow_html=True)
        close_card()
        st.divider()

        open_card("AI Assistant")
        st.markdown("### Ask Questions About Document")
        user_question = st.text_input(
            "Ask a question about the document",
            placeholder="Ask something like: What is the final decision?",
        )
        if user_question.strip():
            with st.spinner("Finding answer..."):
                answer = answer_question(user_question, extracted_text, extracted_data)
            st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="helper-text">Enter a question to get started</div>', unsafe_allow_html=True)
        close_card()
        st.divider()

        with st.expander("View Extracted Text"):
            st.text_area("Extracted Text", value=extracted_text, height=320)

    except ValueError as error:
        st.error(str(error))
    except Exception:
        st.error("Something went wrong while processing the PDF.")


if __name__ == "__main__":
    main()
