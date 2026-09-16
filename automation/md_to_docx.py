# -*- coding: utf-8 -*-
"""
md_to_docx.py — 将简洁 Markdown（标题/引用/无序列表/表格/段落/**加粗**/`等宽`）
转换为 Word .docx。仅使用 Python 标准库（zipfile + XML 手写 OOXML），无需联网安装依赖。
用法: python md_to_docx.py <input.md> <output.docx>
"""
import sys, re, zipfile, html

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def inline_runs(text):
    """把文本切成带格式的 run 片段: **粗体**、`等宽`。返回 XML runs 字符串。"""
    out = []
    pos = 0
    tokens = re.split(r'(\*\*.+?\*\*|`[^`]+`)', text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            inner = esc(tok[2:-2])
            out.append('<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % inner)
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            inner = esc(tok[1:-1])
            out.append('<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/></w:rPr>'
                       '<w:t xml:space="preserve">%s</w:t></w:r>' % inner)
        else:
            out.append('<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % esc(tok))
    return ''.join(out)

def para(xml_runs, style=None, indent=None):
    ppr = ''
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    if indent:
        ppr += '<w:ind w:left="%d"/>' % indent
    return '<w:p>%s%s</w:p>' % (ppr, xml_runs)

def run(text, bold=False):
    rpr = '<w:rPr><w:b/></w:rPr>' if bold else ''
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(text))

def cell(text, header=False, width=None):
    tcpr = ''
    if header:
        tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="D9E2F3"/>'
    ppr = '<w:pPr><w:pStyle w:val="CompactCell"/></w:pPr>'
    rpr = '<w:rPr><w:b/></w:rPr>' if header else ''
    xmlruns = ''.join('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(c)) for c in [text])
    return '<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>' % (tcpr, '<w:p>%s</w:p>' % xmlruns)

def table(rows):
    ncols = max(len(r) for r in rows)
    grid = ''.join('<w:gridCol w:w="%d"/>' % (int(9000 / ncols)) for _ in range(ncols))
    body = []
    for ri, row in enumerate(rows):
        cells = row + [''] * (ncols - len(row))
        body.append('<w:tr>' + ''.join(cell(c, header=(ri == 0)) for c in cells) + '</w:tr>')
    borders = ('<w:tblBorders>'
               + ''.join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>' % s
                         for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
               + '</w:tblBorders>')
    return ('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>%s'
            '<w:tblLayout w:type="autofit"/><w:tblCellMar>'
            '<w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/>'
            '<w:top w:w="40" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/>'
            '</w:tblCellMar></w:tblPr><w:tblGrid>%s</w:tblGrid>%s</w:tbl>' % (borders, grid, ''.join(body)))

def parse_md(text):
    blocks = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            level = min(len(m.group(1)), 3)
            blocks.append(('h%d' % level, m.group(2)))
            i += 1
            continue
        if re.match(r'^\s*([-*_])\1{2,}\s*$', line.strip()):
            i += 1
            continue  # hr 分隔线忽略
        if line.lstrip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            if len(rows) >= 2:
                rows = [rows[0]] + rows[2:]
            blocks.append(('table', rows))
            continue
        if line.lstrip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            blocks.append(('table', rows))
            continue
        if line.lstrip().startswith('- '):
            items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                items.append(lines[i].strip()[2:].strip())
                i += 1
            blocks.append(('bullets', items))
            continue
        if line.lstrip().startswith('> '):
            paras = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                paras.append(lines[i].strip()[2:].strip())
                i += 1
            blocks.append(('quote', paras))
            continue
        # 普通段落（合并到空行为止）
        paras = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#', '- ', '|', '> ')):
            paras.append(lines[i].strip())
            i += 1
        blocks.append(('para', ' '.join(paras)))
    return blocks

def build_document(blocks):
    parts = []
    for kind, data in blocks:
        if kind.startswith('h'):
            parts.append(para(inline_runs(data), style={'h1': 'Heading1', 'h2': 'Heading2', 'h3': 'Heading3'}[kind]))
        elif kind == 'para':
            parts.append(para(inline_runs(data)))
        elif kind == 'quote':
            for q in data:
                r = '<w:r><w:rPr><w:i/><w:color w:val="595959"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % esc(q)
                parts.append('<w:p>%s</w:p>' % r)
        elif kind == 'bullets':
            for item in data:
                parts.append(para('\u2022\u00a0\u00a0' + inline_runs(item), indent=360))
        elif kind == 'table':
            parts.append(table(data))
            parts.append('<w:p/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>%s<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
            'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'
            % ''.join(parts))

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/>
<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>
<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="CompactCell"><w:name w:val="CompactCell"/>
<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="160" w:line="300" w:lineRule="auto"/>
<w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120" w:line="300" w:lineRule="auto"/>
<w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="27"/><w:szCs w:val="27"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="220" w:after="100" w:line="300" w:lineRule="auto"/>
<w:outlineLvl w:val="2"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
</w:styles>'''

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, 'r', encoding='utf-8') as f:
        text = f.read()
    blocks = parse_md(text)
    document = build_document(blocks)
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', RELS)
        z.writestr('word/document.xml', document)
        z.writestr('word/styles.xml', STYLES)
        z.writestr('word/_rels/document.xml.rels', DOC_RELS)
    print('written:', dst, 'bytes=', len(document))

if __name__ == '__main__':
    main()
