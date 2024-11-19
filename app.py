from flask import Flask, render_template, abort, request
import markdown
import os
from ai_reviewer.firebase_utils import FirebaseManager

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='/static')
firebase_manager = FirebaseManager()

@app.route('/')
def hello():
    prev = request.args.get('prev', default="", type=str)
    after = request.args.get('after', default="", type=str)
    if after == "None":
        after = None

    search_query = request.args.get('search', default="", type=str)

    items = firebase_manager.paginate(limit=10, last_doc_id=after)
    current = items[0].id if items else None
    after = items[-1].id if items and len(items) == 10 else None
    if items:
        for item in items:
            item.review_time = item.review_time.strftime("%Y-%m-%d %H:%M")

    return render_template('index.html', posts=items, prev=prev, after=after, current=current, search_query=search_query)

DOC_FORMAT = """
- Authors: {authors}
- URL: [{url}]({url})

## TL;DR
{tldr}

## AI Review
{markdown}
""".strip()

def replace_image_links(content, paper_id, images):
    for image in images:
        image_name = f"({image})"

        if image_name in content:
            image_url = firebase_manager.get_image_download_url(paper_id, image)
            replace_url = f"({image_url})"
            content = content.replace(image_name, replace_url)

    return content


def load_paper(paper_id):
    try:
        doc = firebase_manager.get_by_id(paper_id)
        content = DOC_FORMAT.format(
            title=doc.title,
            tldr=doc.tldr,
            url=doc.url,
            authors=doc.authors,
            markdown=doc.review
        )
        content = replace_image_links(content, paper_id, doc.image_files)
        # Markdown을 HTML로 변환
        html_content = markdown.markdown(
            content.replace("\\n", "\n"),
            extensions=['meta', 'fenced_code', 'tables']
        )
        first_image = doc.image_files[0] if doc.image_files else None
        if first_image:
            first_image_url = firebase_manager.get_image_download_url(paper_id, first_image)
        else:
            first_image_url = None
            
        return {
            "content": html_content,
            "title": doc.title,
            "author": doc.authors,
            "description": doc.tldr,
            "review_time": doc.review_time.strftime("%Y-%m-%d %H:%M"),
            "first_image": first_image_url
        }
    except FileNotFoundError:
        return None

@app.route('/review/<paper_id>')
def review_paper(paper_id):
    content = load_paper(paper_id)
    if content is None:
        abort(404)
    return render_template('paper_test.html', **content)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)