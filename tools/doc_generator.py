"""
Document generation tool supporting PDF, DOCX, XLSX, CSV, Markdown, and TXT files.
"""

import os
import uuid
from typing import Dict, Any, List, Optional

def generate_document(
    format_type: str,
    title: str,
    content: str,
    filename: Optional[str] = None,
    table_data: Optional[List[List[Any]]] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a document file (PDF, DOCX, XLSX, CSV, Markdown, TXT) and returns file details.
    Ensures per-user artifact directory isolation when user_id is supplied.
    """
    import re
    outputs_dir = os.path.join(os.getcwd(), "outputs")
    if user_id:
        safe_uid = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(user_id).strip().lower())
        outputs_dir = os.path.join(outputs_dir, safe_uid)
    os.makedirs(outputs_dir, exist_ok=True)

    format_type = format_type.lower().strip()
    if not filename:
        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        clean_title = clean_title.replace(" ", "_").lower()[:30] or "document"
        filename = f"{clean_title}_{uuid.uuid4().hex[:6]}.{format_type}"

    file_path = os.path.join(outputs_dir, filename)

    try:
        if format_type == "pdf":
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors

            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            flowables = []

            # Title
            title_style = styles["Heading1"]
            flowables.append(Paragraph(title, title_style))
            flowables.append(Spacer(1, 14))

            # Body Paragraphs
            body_style = styles["Normal"]
            for paragraph_text in content.split("\n\n"):
                if paragraph_text.strip():
                    flowables.append(Paragraph(paragraph_text.replace("\n", "<br/>"), body_style))
                    flowables.append(Spacer(1, 8))

            # Optional table
            if table_data and len(table_data) > 0:
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F8F9F9")),
                    ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#BDC3C7")),
                ]))
                flowables.append(t)

            doc.build(flowables)

        elif format_type in ["docx", "doc"]:
            import docx
            doc = docx.Document()
            doc.add_heading(title, level=0)

            for block in content.split("\n\n"):
                if block.startswith("### "):
                    doc.add_heading(block.replace("### ", ""), level=2)
                elif block.startswith("## "):
                    doc.add_heading(block.replace("## ", ""), level=1)
                elif block.startswith("- "):
                    for line in block.splitlines():
                        doc.add_paragraph(line.lstrip("- *"), style='List Bullet')
                else:
                    if block.strip():
                        doc.add_paragraph(block.strip())

            if table_data and len(table_data) > 0:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                table.style = 'Light Shading Accent 1'
                for r_idx, row in enumerate(table_data):
                    for c_idx, val in enumerate(row):
                        table.cell(r_idx, c_idx).text = str(val)

            doc.save(file_path)

        elif format_type in ["xlsx", "xls"]:
            import pandas as pd
            if table_data and len(table_data) > 1:
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
            else:
                lines = [line.split(",") for line in content.splitlines() if line.strip()]
                if lines and len(lines) > 1:
                    df = pd.DataFrame(lines[1:], columns=lines[0])
                else:
                    df = pd.DataFrame({"Title": [title], "Content": [content]})
            df.to_excel(file_path, index=False)

        elif format_type == "csv":
            import pandas as pd
            if table_data and len(table_data) > 1:
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                df.to_csv(file_path, index=False)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

        elif format_type in ["md", "markdown", "txt"]:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{content}")

        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        file_size_kb = round(os.path.getsize(file_path) / 1024, 2)
        return {
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "format": format_type,
            "size_kb": file_size_kb
        }

    except Exception as e:
        return {"success": False, "error": f"Failed generating {format_type}: {str(e)}"}
