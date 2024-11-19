from datetime import datetime
from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore, storage
from firebase_admin import credentials
import os, io
import base64
from PIL import Image
import json
import tempfile
import markdown


class PaperStore(BaseModel):
    id: str = ""
    title: str
    abstract: str
    authors: str
    url: str 
    review_time: datetime = datetime.now()
    markdown: str = ""
    review: str = ""
    tldr: str = ""
    image_files: list[str] = []

class FirebaseManager:
    def __init__(self):
        project_id = os.environ["FIREBASE_PROJECT_ID"]

        app_options = {
            'projectId': project_id,
            'storageBucket': f"{project_id}.firebasestorage.app"
            }
        cred = credentials.Certificate("firebase-credentials.json")
        self.app = firebase_admin.initialize_app(cred, options=app_options)
        self.db = firestore.client(self.app)
        self.collection = self.db.collection("papers")
        self.storage = storage.bucket(app=self.app)


    def paginate(self, limit: int = 20, last_doc_id: str = None, search_query: str = None) -> list[PaperStore]:
        if search_query:
            query = self.collection.where("title", ">=", search_query).where("title", "<=", search_query + "\uf8ff") \
                .order_by("review_time", direction=firestore.Query.DESCENDING) 
        else:
            query = self.collection.order_by("review_time", direction=firestore.Query.DESCENDING) 

        if last_doc_id:
            last_doc = self.collection.document(last_doc_id).get()
            query = query.start_after(last_doc)
        
        query = query.limit(limit)
        items = query.get()
        outputs = []
        for item in items:
            d = item.to_dict()
            if d:
                d["id"] = item.id
                outputs.append(PaperStore(**d))
        return outputs
                
    def get_by_url(self, url: str) -> list:
        docs = self.collection.where("url", "==", url).get()
        if len(docs) == 0:
            return None, None
        paper = docs[0].to_dict()
        if "id" not in paper:
            paper["id"] = docs[0].id
            
        return docs[0].id, PaperStore(**paper)
    
    def get_by_id(self, paper_id: str):
        doc = self.collection.document(paper_id).get()
        item = doc.to_dict()
        if item:
            return PaperStore(**item)
        return None

    def add_paper(self, paper: PaperStore):
        _, ref = self.collection.add(paper.model_dump())
        print(f"Added paper {ref.id} to Firestore: {paper.title}")
        return ref.id
    
    def upload_image(self, paper_id: str, base64_images: list[dict]):
        """
        base64_images: [{"image_name": "image1.png", "image": "base64-encoded-image-data"}]
        """

        for image in base64_images:
            image_data = base64.b64decode(image["image"])
            image_name = image["image_name"]
            ext = image_name.split(".")[-1].lower()
            blob = self.storage.blob(f"images/{paper_id}/{image_name}")
            blob.upload_from_string(image_data, content_type=f"image/{ext}")

    def get_image_download_url(self, paper_id: str, image_name: str):
        blob = self.storage.blob(f"images/{paper_id}/{image_name}")
        return blob.generate_signed_url(expiration=int(datetime.now().timestamp() + 3600))

    def delete_review(self, paper_id: str):
        self.collection.document(paper_id).delete()
        print(f"Deleted paper {paper_id} from Firestore.")

        # delete images from firebase storage
        blobs = self.storage.list_blobs(prefix=f"images/{paper_id}")
        for blob in blobs:
            blob.delete()
            print(f"Deleted image {blob.name} from Firebase Storage.")

if __name__ == "__main__":
    manager = FirebaseManager()
    paper = PaperStore(
        title="Test Title",
        abstract="Test Abstract",
        authors="Test Authors",
        url="https://arxiv.org/abs/2401.01854",
        review_time=datetime.now(),
        markdown="Test Markdown",
        tldr="Test TLDR",
    )
    # paper_id = manager.add_paper(paper)

    images = json.load(open("test.json"))['images']
    paper_id = "epCavYGV4JVBOqVdAluO"
    manager.upload_image(paper_id, images)
    print("Done.")