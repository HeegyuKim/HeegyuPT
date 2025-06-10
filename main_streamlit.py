import streamlit as st
from pptgen import create_presentation_from_report



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

def process_presentation(prompt, files):
    # Call the function to create a presentation from the report
    try:
        output_filename = create_presentation_from_report(prompt, files[0], model="gpt-4.1-mini")
        st.success("PPT generated successfully!")

        st.download_button(
            label="Download PPT",
            data=output_filename,
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    except Exception as e:
        st.error(f"An error occurred while generating the PPT: {e}")
        return


if st.button("Generate PPT"):
    
    if files:
        # check files
        for file in files:
            if file.type not in ["application/pdf", "text/markdown", "text/plain"]:
                st.error("Unsupported file type. Please upload a PDF, Markdown, or Text file.")
                st.stop()

        with st.spinner("Generating PPT..."):
            process_presentation(prompt, files)
    else:
        st.error("Please upload a report file.")
        