from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

IMAGE_RESOLUTION_SCALE = 2.0

pipeline_options = PdfPipelineOptions(do_table_structure=True)
# pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model
pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
pipeline_options.generate_page_images = True
pipeline_options.generate_table_images = True
pipeline_options.generate_picture_images = True

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
result = doc_converter.convert(source, max_num_pages=9)
print(result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED))  # output: "### Docling Technical Report[...]"