"""A4 exports keep the whole slide, its proportions and selectable PDF text."""
from io import BytesIO

from pypdf import PdfReader, PdfWriter, Transformation


def a4_pdf(content, orientation='landscape'):
    if orientation not in {'portrait', 'landscape'}:
        raise ValueError('PDF 방향은 portrait 또는 landscape로 지정하세요.')
    width, height = 595.2756, 841.8898
    if orientation == 'landscape':
        width, height = height, width
    writer = PdfWriter()
    for source in PdfReader(BytesIO(content)).pages:
        source.transfer_rotation_to_content()
        scale = min(width / float(source.mediabox.width), height / float(source.mediabox.height))
        x = (width - float(source.mediabox.width) * scale) / 2
        y = (height - float(source.mediabox.height) * scale) / 2
        target = writer.add_blank_page(width=width, height=height)
        target.merge_transformed_page(source, Transformation().scale(scale).translate(x, y))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
