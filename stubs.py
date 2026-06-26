"""GOOGLE_STUB=true 用のスタブクライアント。

実Google APIと同じ呼び出し形（service.spreadsheets().values().append(...).execute()）を
最小限で模倣し、ネットワーク無しでコアループとテストを回せるようにする。
追記された行はメモリに蓄積され、テストから検証できる。
"""
import logging

log = logging.getLogger("screenlog.stub")


class _Executable:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


# ---- Sheets stub ----
class _StubValues:
    def __init__(self, store):
        self._store = store

    def append(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        rows = (body or {}).get("values", [])

        def _do():
            self._store.appended_rows.extend(rows)
            log.info("[STUB Sheets] append %d row(s) to %s!%s", len(rows), spreadsheetId, range)
            return {"updates": {"updatedRows": len(rows)}}

        return _Executable(_do)

    def get(self, spreadsheetId=None, range=None):
        def _do():
            return {"values": list(self._store.appended_rows)}

        return _Executable(_do)


class _StubSpreadsheets:
    def __init__(self, store):
        self._store = store

    def values(self):
        return _StubValues(self._store)


class StubSheetsService:
    """append された行を appended_rows に蓄積する Sheets スタブ。"""

    def __init__(self):
        self.appended_rows: list[list] = []

    def spreadsheets(self):
        return _StubSpreadsheets(self)


# ---- Gmail stub ----
class _StubMessages:
    def __init__(self, store):
        self._store = store

    def send(self, userId=None, body=None):
        def _do():
            self._store.sent.append(body)
            log.info("[STUB Gmail] send message (userId=%s)", userId)
            return {"id": "stub-message-id"}

        return _Executable(_do)


class _StubUsers:
    def __init__(self, store):
        self._store = store

    def messages(self):
        return _StubMessages(self._store)


class StubGmailService:
    """send されたメッセージを sent に蓄積する Gmail スタブ。"""

    def __init__(self):
        self.sent: list[dict] = []

    def users(self):
        return _StubUsers(self)


# ---- Docs stub ----
class _StubDocuments:
    def __init__(self, store):
        self._store = store

    def create(self, body=None):
        def _do():
            self._store.created.append(body or {})
            return {"documentId": "stub-doc-id"}

        return _Executable(_do)

    def batchUpdate(self, documentId=None, body=None):
        def _do():
            for req in (body or {}).get("requests", []):
                text = req.get("insertText", {}).get("text")
                if text is not None:
                    self._store.inserted_text.append(text)
            log.info("[STUB Docs] batchUpdate on %s", documentId)
            return {"documentId": documentId}

        return _Executable(_do)


class StubDocsService:
    """create/batchUpdate を記録する Docs スタブ。"""

    def __init__(self):
        self.created: list[dict] = []
        self.inserted_text: list[str] = []

    def documents(self):
        return _StubDocuments(self)
