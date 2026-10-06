from connectors.law_go_kr import _parse_article_text

PAGE = (
    "제18조의4(캠핑용자동차의 안전기준) ① 구 조문 내용. 제18조의5 "
    "제18조의4(사이버보안) 자동차의 전기ㆍ전자장치는 다음 각 호의 기준에 적합해야 한다. "
    "1. 주요 구성요소가 식별되도록 할 것 2. 위험이 평가되도록 할 것 가. 구성요소 "
    "[본조신설 2025. 8. 14.] 제18조의4 제18조의5(소프트웨어) ① 버전을 확인할 수 있어야 한다."
)


def test_takes_last_version_of_article():
    title, body = _parse_article_text(PAGE, "18-4")
    assert title.endswith("제18조의4(사이버보안)")
    assert "구 조문" not in body
    assert "\n\n1. 주요" in body and "\n\n2. 위험" in body
    assert not body.rstrip().endswith("제18조의4")


def test_new_article_found_without_label():
    title, body = _parse_article_text(PAGE, "18-5")
    assert "소프트웨어" in title and body.startswith("제18조의5(소프트웨어)")


def test_missing_article_returns_none():
    assert _parse_article_text(PAGE, "99") is None


def test_ignores_supplementary_provisions():
    page = PAGE + " 부칙 <제1234호, 2026. 6. 5.> 제18조의4(다른 법령의 개정) 부칙 내용."
    title, _ = _parse_article_text(page, "18-4")
    assert title.endswith("제18조의4(사이버보안)")


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeSession:
    def __init__(self, text):
        self._text = text
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return _FakeResp(self._text)


def test_resolves_current_version_from_law_name_page():
    from connectors import law_go_kr
    law_go_kr._current_cache.clear()
    page = '<iframe src="/LSW//lsInfoP.do?lsiSeq=288083&amp;chrClsCd=010202&amp;efYd=20260710"></iframe>'
    session = _FakeSession(page)
    current = law_go_kr.resolve_current_version(session, "270023")
    assert current == {"lsiSeq": "288083", "efYd": "20260710", "chrClsCd": "010202"}
    assert "법령/" in session.urls[0]
    law_go_kr._current_cache.clear()
