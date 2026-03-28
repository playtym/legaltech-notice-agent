import io
import zipfile
from datetime import datetime

class EDaakhilPackager:
    @staticmethod
    def create_export_zip(notice_text: str, pdf_bytes: bytes, complainant_name: str) -> bytes:
        """
        Creates a structurally compliant .zip file for the E-Daakhil government portal.
        Includes a compiled index.txt, the paginated Notice PDF, and a placeholder for evidence.
        """
        mem_zip = io.BytesIO()
        
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. Provide the main notice PDF
            zf.writestr("1_Legal_Notice_Signed.pdf", pdf_bytes)
            
            # 2. Add an Index / Memo of Parties
            index_content = f"""MEMO OF PARTIES & INDEX
Date: {datetime.now().strftime('%d-%m-%Y')}
Complainant: {complainant_name}

FILES INCLUDED IN THIS EXPORT:
1. 1_Legal_Notice_Signed.pdf - The generated statutory notice sent to the opposing party.
2. 2_Evidence_Annexures.pdf - (Please append your screenshots/invoices here before upload).
3. 3_ID_Proof.pdf - (Please append your Aadhaar/PAN here before upload).

This packet is pre-formatted for rapid submission to the District Consumer Disputes Redressal Commission via E-Daakhil.
"""
            zf.writestr("0_Index_and_Memo.txt", index_content)
            
            # 3. Dummy placeholder for evidence to guide the user
            zf.writestr("2_Evidence_Annexures_PLACEHOLDER.txt", "Replace this file with a PDF containing your merged evidence screenshots.")
            
        return mem_zip.getvalue()
