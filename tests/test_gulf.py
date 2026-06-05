from connectors.gulf import master_pdf_live, MASTER_URL

class FakeResp:
    def __init__(self, ct="application/pdf", status=200):
        self.headers = {"Content-Type": ct}; self.status_code = status; self.encoding = "utf-8"
    def raise_for_status(self): pass

class FakeSession:
    def __init__(self, resp=None, raises=False):
        self._resp = resp or FakeResp(); self._raises = raises; self.urls = []
    def get(self, url, **kw):
        self.urls.append(url)
        if self._raises:
            raise RuntimeError("boom")
        return self._resp
    def close(self): pass

def test_master_pdf_live_true_for_pdf_200():
    assert master_pdf_live(FakeSession(FakeResp("application/pdf", 200))) is True

def test_master_pdf_live_false_for_404():
    assert master_pdf_live(FakeSession(FakeResp("text/html", 404))) is False

def test_master_pdf_live_false_on_exception():
    assert master_pdf_live(FakeSession(raises=True)) is False
