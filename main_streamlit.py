from dotenv import load_dotenv
import os
import asyncio
import streamlit as st
import tempfile
from pptgen import create_presentation_from_report
import litellm
from traceback import print_exc
load_dotenv()

if "APP_PASSWORD" in os.environ:
    if not st.session_state.get("login", False):
        pw = st.text_input("Enter password to access the app", type="password")
        if st.button("Login"):
            if pw == os.getenv("APP_PASSWORD"):
                st.session_state.login = True
            else:
                st.error("Incorrect password. Please try again.")
                st.stop()
        else:
            st.stop()


st.title("PPT Generator")

prompt = st.text_area(
    "Enter your prompt here",
    placeholder="Type your prompt for the PPT generation... (e.g., 'Create a PPT about AI advancements')",
    height=200,
)

files = st.file_uploader(
    "Upload a report file (PDF, Markdown, or Text)",
    type=["pdf", "md", "txt"],
    accept_multiple_files=False,
)

use_web_search = st.checkbox(
    "Use web search to gather additional information for the PPT",
    value=False,
)

def files_to_report(files):
    report = ""
    for file in files:
        if file.endswith(".pdf"):
            # Handle PDF files
            from PyPDF2 import PdfReader
            reader = PdfReader(file)
            report += f"\n\n---\n\nReport from {file.name}:\n\n"
            report += "\n".join(page.extract_text() for page in reader.pages)
        elif file.endswith(".md") or file.endswith(".txt"):
            # Handle Markdown or Text files
            report += f"\n\n---\n\nReport from {file.name}:\n\n"
            report += file.read().decode("utf-8")
        else:
            st.error(f"Unsupported file type: {file.type}")
            return None
    return report

def process_presentation(prompt, files):
    # Call the function to create a presentation from the report
    try:
        report = files_to_report(files)
        output_filename = asyncio.run(create_presentation_from_report(prompt, report, model="gpt-4.1-mini"))
        st.success("PPT generated successfully!")

        st.download_button(
            label="Download PPT",
            data=output_filename,
            file_name=output_filename,
        )
    except Exception as e:
        st.error(f"An error occurred while generating the PPT: {e}")
        print_exc()
        return
    
def process_web_search(prompt):
    prompt = f"Search the web and create a report for information related to:\n\n{prompt}"
    output = litellm.completion(
        # model="openrouter/perplexity/sonar-deep-research",
        model="openrouter/perplexity/sonar-pro",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=65536,
    )
    result = output.choices[0].message.content
    
    if hasattr(output, "annotations"):
        for annotation in output.annotations:
            if annotation['type'] == 'url_citation':
                cite = annotation['url_citation']
                start_index, end_index = cite['start_index'], cite['end_index']
                if start_index == end_index:
                    index = f"[{start_index + 1}]"
                else:
                    index = f"[{start_index + 1}-{end_index + 1}]"
                result += f"\n\nSource: {annotation.source_url}"


if st.button("Generate PPT"):
    
    if files or use_web_search:
        if not files:
            files = []
        elif not isinstance(files, list):
            files = [files]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            for file in files:
                # Save the uploaded file to the temporary directory
                temp_file_path = os.path.join(temp_dir, file.name)
                with open(temp_file_path, "wb") as f:
                    f.write(file.read())
                file_paths.append(temp_file_path)

            if use_web_search:
                with st.spinner("Performing web search..."):
                    web_search_results = process_web_search(prompt)
                    prompt += f"\n\n---\n\nWeb search results:\n{web_search_results}"
                
                with st.expander("Web Search Results"):
                    st.markdown(web_search_results)

            with st.spinner("Generating PPT..."):
                process_presentation(prompt, file_paths)
    else:
        st.error("Please upload a report file or enable web search to generate the PPT.")
        