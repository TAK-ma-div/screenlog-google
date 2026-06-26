"""Google Docs に週次レポートを作成する。"""
import logging

from google_auth import get_docs_service

log = logging.getLogger("screenlog.docs")


def create_report_doc(title: str, body_text: str) -> tuple[str, str]:
    """新規 Google Doc を作成し本文を挿入。(document_id, url) を返す。"""
    service = get_docs_service()
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # 先頭(index=1)に本文を挿入
    service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": body_text}}
            ]
        },
    ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    log.info("Docsレポートを作成: %s", url)
    return doc_id, url
