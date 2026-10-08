from lxml import etree

from ingestion.docx_active_text import W, active_paragraph_text


def _paragraph(inner: str):
    return etree.fromstring(f'<w:p xmlns:w="{W[1:-1]}">{inner}</w:p>')


def test_active_text_keeps_highlight_and_insertions():
    paragraph = _paragraph(
        '<w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>10.5.4.1</w:t></w:r>'
        '<w:ins w:id="1"><w:r><w:t> active</w:t></w:r></w:ins>'
    )
    assert active_paragraph_text(paragraph) == "10.5.4.1 active"


def test_active_text_drops_struck_hidden_and_deleted_runs():
    paragraph = _paragraph(
        '<w:r><w:t>keep</w:t></w:r>'
        '<w:r><w:rPr><w:strike/></w:rPr><w:t> strike</w:t></w:r>'
        '<w:r><w:rPr><w:dstrike/></w:rPr><w:t> double</w:t></w:r>'
        '<w:r><w:rPr><w:vanish/></w:rPr><w:t> hidden</w:t></w:r>'
        '<w:del w:id="2"><w:r><w:delText> deleted</w:delText></w:r></w:del>'
    )
    assert active_paragraph_text(paragraph) == "keep"